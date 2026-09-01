"""
Intelligent Multi-Signal Application Matcher for ApplyTrack AI.

Matches incoming classified email events to existing job application records
using a composite weighted scoring model across:
- Company name (exact & fuzzy)
- Job title (exact & fuzzy)
- Sender email domain
- Recruiter email / name
- Thread ID correlation
- Subject keywords & job URL
- Contextual dates

Thresholds:
- score >= 0.75: High confidence -> Attach automatically
- 0.40 <= score < 0.75: Low confidence -> Route to Human Review (needs_review=True)
- score < 0.40 & has company: New application created (with confidence gating)
"""
import re
import logging
from difflib import SequenceMatcher
from typing import Tuple, Optional, Dict, Any, List
from django.utils import timezone

from apps.applications.models import Application, ApplicationStatus, StatusHistory
from apps.gmail_integration.models import ProcessedEmail

logger = logging.getLogger(__name__)


class ApplicationMatcher:
    """
    Service for robust, multi-signal matching of emails to applications.
    """

    AUTO_ATTACH_THRESHOLD = 0.75
    REVIEW_ATTACH_THRESHOLD = 0.40

    @classmethod
    def match_email_to_application(
        cls,
        email_data: Dict[str, Any],
        user
    ) -> Tuple[Optional[Application], float, bool]:
        """
        Match an email to an existing application or determine if it should create a new one.

        Returns:
            Tuple: (matched_application, match_score, is_new)
        """
        try:
            company = (email_data.get('company') or '').strip()
            job_title = (email_data.get('job_title') or '').strip()
            sender = (email_data.get('sender') or '').strip()
            sender_domain = (email_data.get('sender_domain') or '').strip()
            subject = (email_data.get('subject') or '').strip()
            thread_id = (email_data.get('thread_id') or '').strip()
            job_url = (email_data.get('job_url') or '').strip()

            applications = Application.objects.filter(user=user)

            best_match: Optional[Application] = None
            best_score = 0.0

            for app in applications:
                score = cls._calculate_match_score(
                    app=app,
                    company=company,
                    job_title=job_title,
                    sender=sender,
                    sender_domain=sender_domain,
                    subject=subject,
                    thread_id=thread_id,
                    job_url=job_url
                )

                if score > best_score:
                    best_score = score
                    best_match = app

            # Case 1: High Confidence Match -> Auto Attach
            if best_match and best_score >= cls.AUTO_ATTACH_THRESHOLD:
                logger.debug(f"High confidence match ({best_score:.2f}) for application {best_match.id} ({best_match.company})")
                return best_match, best_score, False

            # Case 2: Ambiguous Match -> Low Confidence -> Route to Human Review
            if best_match and best_score >= cls.REVIEW_ATTACH_THRESHOLD:
                logger.info(f"Ambiguous match ({best_score:.2f}) for application {best_match.id}. Routing to review.")
                return best_match, best_score, False

            # Case 3: New Application Candidate (if entities extracted OR confidence indicates job email)
            classification_conf = float(email_data.get('confidence', 0.8))
            if bool(company or job_title) or classification_conf >= 0.5:
                return None, classification_conf, True

            # Case 4: No Match & Not New
            return None, 0.0, False

        except Exception as e:
            logger.error(f"Application matching exception: {str(e)}")
            return None, 0.0, False

    @classmethod
    def _calculate_match_score(
        cls,
        app: Application,
        company: str,
        job_title: str,
        sender: str,
        sender_domain: str,
        subject: str,
        thread_id: str,
        job_url: str
    ) -> float:
        """
        Calculate composite weighted match score (0.0 to 1.0) using multiple independent signals.
        """
        score = 0.0

        # Signal 1: Thread ID correlation (Strongest signal)
        if thread_id:
            thread_exists = ProcessedEmail.objects.filter(
                application_id=app.id,
                thread_id=thread_id
            ).exists()
            if thread_exists:
                score += 0.40

        # Signal 2: Company Name Matching (Exact & Fuzzy)
        if company and app.company:
            comp_a = cls._normalize_text(company)
            comp_b = cls._normalize_text(app.company)
            if comp_a == comp_b:
                score += 0.35
            else:
                sim = SequenceMatcher(None, comp_a, comp_b).ratio()
                if sim >= 0.85:
                    score += 0.30
                elif sim >= 0.65:
                    score += 0.15

        # Signal 3: Job Title Matching (Exact & Fuzzy)
        if job_title and app.job_title:
            title_a = cls._normalize_text(job_title)
            title_b = cls._normalize_text(app.job_title)
            if title_a == title_b:
                score += 0.25
            else:
                sim = SequenceMatcher(None, title_a, title_b).ratio()
                if sim >= 0.80:
                    score += 0.20
                elif sim >= 0.60:
                    score += 0.10

        # Signal 4: Sender Email Domain Match
        if sender_domain and app.company:
            comp_norm = cls._normalize_text(app.company).replace(' ', '')
            domain_clean = sender_domain.split('.')[0].lower() if '.' in sender_domain else sender_domain.lower()
            if domain_clean in comp_norm or comp_norm in domain_clean:
                score += 0.20

        # Signal 5: Recruiter Email / Name Match
        if sender and (app.recruiter_email or app.recruiter_name):
            if app.recruiter_email and app.recruiter_email.lower() in sender.lower():
                score += 0.25
            elif app.recruiter_name and app.recruiter_name.lower() in sender.lower():
                score += 0.15

        # Signal 6: Subject keyword match
        if subject and app.company:
            if app.company.lower() in subject.lower():
                score += 0.15

        # Signal 7: Job URL Match
        if job_url and app.job_url:
            if job_url.lower() == app.job_url.lower():
                score += 0.30

        return min(score, 1.0)

    @classmethod
    def _normalize_text(cls, text: str) -> str:
        """Strip punctuation and whitespace for clean string matching."""
        if not text:
            return ""
        clean = re.sub(r'[^\w\s]', '', text.lower())
        return ' '.join(clean.split())

    @classmethod
    def create_application_from_email(
        cls,
        email_data: Dict[str, Any],
        user
    ) -> Application:
        """
        Create a new Application record from classified email metadata.
        """
        company = (email_data.get('company') or 'Unknown Company').strip()
        job_title = (email_data.get('job_title') or 'Unknown Position').strip()
        received_at = email_data.get('received_at')
        application_date = received_at.date() if hasattr(received_at, 'date') else timezone.now().date()
        detected_status_str = email_data.get('status', 'Applied')
        confidence = float(email_data.get('confidence', 0.8))
        needs_review = email_data.get('needs_review', False) or (confidence < 0.70)
        review_reason = email_data.get('review_reason', '')

        try:
            status_enum = ApplicationStatus(detected_status_str)
        except ValueError:
            status_enum = ApplicationStatus.APPLIED

        app = Application.objects.create(
            user=user,
            company=company,
            job_title=job_title,
            application_date=application_date,
            current_status=status_enum,
            is_ai_detected=True,
            is_manual=False,
            confidence=confidence,
            needs_review=needs_review,
            review_reason=review_reason if needs_review else None,
            last_activity_date=timezone.now(),
            last_email_date=timezone.now()
        )

        # Create initial status history entry
        StatusHistory.objects.create(
            application=app,
            previous_status=None,
            new_status=status_enum,
            source=email_data.get('tier_used', 'email_sync'),
            confidence=confidence,
            evidence=email_data.get('reasoning', f"Created from email {email_data.get('subject', '')}")
        )

        return app
