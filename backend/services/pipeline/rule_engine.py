"""
Deterministic Email Rule Engine for ApplyTrack AI.

Provides high-precision pattern matching across structured evidence families:
- Subject patterns
- Body phrase patterns
- Sender and ATS domain signals
- Negative patterns & disambiguation context
- Entity extraction heuristics (company, job title, event type, status)

When rule evidence is sufficiently high (>= 70/100), yields a deterministic final decision,
bypassing external AI API calls completely.
"""
import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class RuleCategory(str, Enum):
    REJECTION = "REJECTION"
    INTERVIEW = "INTERVIEW"
    ASSESSMENT = "ASSESSMENT"
    OFFER = "OFFER"
    APPLICATION_RECEIVED = "APPLICATION_RECEIVED"
    WITHDRAWAL = "WITHDRAWAL"
    RECRUITER_CONTACT = "RECRUITER_CONTACT"
    UNDER_REVIEW = "UNDER_REVIEW"
    NON_JOB = "NON_JOB"
    OTHER = "OTHER"


@dataclass
class ClassificationRule:
    """Structured rule definition with pattern families and weights."""
    name: str
    category: RuleCategory
    subject_patterns: List[str] = field(default_factory=list)
    body_patterns: List[str] = field(default_factory=list)
    negative_patterns: List[str] = field(default_factory=list)
    subject_weight: int = 35
    body_weight: int = 35
    priority: int = 100
    enabled: bool = True


class RuleEngine:
    """
    Modular deterministic rule engine evaluating job email patterns.
    """

    HIGH_CONFIDENCE_THRESHOLD = 70  # Points out of 100 required for final deterministic decision
    MIN_JOB_EVIDENCE_THRESHOLD = 30

    # ATS & Recruiter sender domains
    ATS_DOMAINS = {
        'greenhouse.io', 'gh.io', 'lever.co', 'workday.com', 'myworkday.com',
        'icims.com', 'smartrecruiters.com', 'ashbyhq.com', 'jobvite.com',
        'taleo.net', 'breezy.hr', 'pinpointhq.com', 'workable.com',
        'rippling.com', 'recruitee.com', 'hirevue.com', 'gem.com',
        'successfactors.com', 'kekamail.com', 'keka.com', 'darwinbox.in',
        'darwinbox.com', 'hackerrank.net', 'hackerrank.com', 'connectedcareers.com',
        'oraclecloud.com', 'phenompeople.com'
    }

    GENERIC_JOB_PLATFORMS = {
        'linkedin.com', 'indeed.com', 'naukri.com', 'glassdoor.com',
        'monster.com', 'ziprecruiter.com', 'wellfound.com', 'angel.co'
    }

    # Job platform sender prefixes
    RECRUITER_SENDER_PATTERNS = [
        r'careers@', r'recruiting@', r'jobs@', r'talent@', r'hr@',
        r'talentacquisition@', r'hiring@', r'no-reply@', r'noreply@'
    ]

    # Non-job newsletter & digest negative indicators
    NON_JOB_PATTERNS = [
        r'\b(?:weekly digest|daily digest|job recommendations|jobs you may be interested in)\b',
        r'\b(?:top jobs for you|recommended jobs|new jobs matching your search|job alerts?)\b',
        r'\b(?:view all \d+ jobs|see more jobs|sponsored jobs|unsubscribe from job alerts)\b',
        r'\b(?:security alert|password reset|verify your email|order confirmation|receipt for)\b',
        r'\b(?:invoice|shipping confirmation|track your package|newsletter)\b'
    ]

    # Registered Rule Sets
    RULES: List[ClassificationRule] = [
        # 1. REJECTION
        ClassificationRule(
            name="rejection_family",
            category=RuleCategory.REJECTION,
            subject_patterns=[
                r'\b(?:update on your application|application status|your application (?:at|to|with)|status of your application)\b',
                r'\b(?:decision on your application|candidacy update|regarding your application)\b',
                r'\b(?:thank you for your interest in|application outcome)\b'
            ],
            body_patterns=[
                r'\b(?:not moving forward|not proceeding|not selected|unsuccessful|other candidates)\b',
                r'\b(?:position filled|application declined|will not continue|chosen another candidate)\b',
                r'\b(?:decided to pursue other|after careful consideration|will not be moving forward)\b',
                r'\b(?:not moving you forward|not to move forward|decided not to proceed)\b',
                r'\b(?:decided to move forward with other|decided to move ahead with other)\b',
                r'\b(?:unable to offer you an interview|cannot offer you an interview)\b',
                r'\b(?:we regret to inform you|unfortunately,? we have decided)\b'
            ],
            negative_patterns=[
                r'\b(?:if you are not moving forward|not selected by mistake|do not worry)\b',
                r'\b(?:before we make a decision|while we are deciding)\b'
            ],
            subject_weight=30,
            body_weight=45,
            priority=10
        ),

        # 2. INTERVIEW
        ClassificationRule(
            name="interview_family",
            category=RuleCategory.INTERVIEW,
            subject_patterns=[
                r'\b(?:interview (?:invitation|invite|confirmation|schedule|availability|request))\b',
                r'\b(?:invitation to (?:interview|chat|meet)|schedule (?:an?|your) interview)\b',
                r'\b(?:technical interview|phone screen|interview details|virtual interview|preliminary screening)\b',
                r'\b(?:video interview|round 1 interview|first round interview|final round interview)\b'
            ],
            body_patterns=[
                r'\b(?:interview invitation|schedule (?:an?|your) interview|technical interview|virtual interview)\b',
                r'\b(?:select a time|interview availability|next interview stage|invite you to interview)\b',
                r'\b(?:like to schedule a (?:call|phone screen|chat|video call|meeting))\b',
                r'\b(?:confirm your interview|availability for an? (?:interview|introductory call|preliminary screening))\b',
                r'\b(?:book a time on my calendar|schedule a \d+-minute|google meet|zoom link)\b',
                r'\b(?:pleased to invite you for an? interview|next step is an? interview)\b',
                r'\b(?:interview with our team|meet with the hiring manager)\b'
            ],
            negative_patterns=[
                r'\b(?:do not require an interview|no interview required)\b',
                r'\b(?:tips for interviewing|how to prepare for (?:your )?interview|interview advice|interview tips)\b',
                r'\b(?:prepare for your next interview|mock interview)\b'
            ],
            subject_weight=35,
            body_weight=40,
            priority=20
        ),

        # 3. ASSESSMENT
        ClassificationRule(
            name="assessment_family",
            category=RuleCategory.ASSESSMENT,
            subject_patterns=[
                r'\b(?:online assessment|coding assessment|technical assessment|coding test)\b',
                r'\b(?:hackerrank|codility|take-home (?:assignment|task|challenge)|skills assessment)\b',
                r'\b(?:coderbyte|codesignal|assessment invitation)\b'
            ],
            body_patterns=[
                r'\b(?:online assessment|coding assessment|technical assessment|assessment link)\b',
                r'\b(?:coding test|complete the assessment|hackerrank test|codility challenge)\b',
                r'\b(?:take-home test|complete the test within|technical challenge|assessment on)\b',
                r'\b(?:codesignal assessment|invitation to take the test|timed assessment)\b'
            ],
            negative_patterns=[
                r'\b(?:how to prepare for coding|tips for assessment|practice assessment|free assessment test)\b',
                r'\b(?:assessment guide|prepare for technical assessment)\b'
            ],
            subject_weight=35,
            body_weight=40,
            priority=30
        ),

        # 4. OFFER
        ClassificationRule(
            name="offer_family",
            category=RuleCategory.OFFER,
            subject_patterns=[
                r'\b(?:offer of employment|job offer|offer letter|employment offer)\b',
                r'\b(?:welcome to the team|congratulations from)\b'
            ],
            body_patterns=[
                r'\b(?:offer of employment|pleased to offer|job offer|offer letter)\b',
                r'\b(?:delighted to offer|congratulations on your offer|formal offer of employment)\b',
                r'\b(?:attached (?:is )?your offer|signing bonus|base salary of|annual compensation of)\b',
                r'\b(?:pleased to extend an offer|excited to offer you the position)\b'
            ],
            negative_patterns=[
                r'\b(?:special offer|promotional offer|discount offer|limited time offer|marketing offer)\b',
                r'\b(?:course offer|training offer|subscription offer)\b'
            ],
            subject_weight=35,
            body_weight=45,
            priority=40
        ),

        # 5. APPLICATION RECEIVED
        ClassificationRule(
            name="application_received_family",
            category=RuleCategory.APPLICATION_RECEIVED,
            subject_patterns=[
                r'\b(?:application received|thank you for applying|application submitted)\b',
                r'\b(?:application confirmation|we received your application|thank you for your interest)\b',
                r'\b(?:your application to|acknowledgement of application|application for .*? received)\b',
                r'\bindeed application:\b'
            ],
            body_patterns=[
                r'\b(?:application received|thank you for applying|application submitted)\b',
                r'\b(?:application successfully received|we have received your application)\b',
                r'\b(?:thank you for submitting your application|confirm receipt of your application)\b',
                r'\b(?:currently reviewing your application|received your application for the|your application was sent to)\b'
            ],
            negative_patterns=[
                r'\b(?:submit your application today|haven\'t applied yet|finish your application)\b',
                r'\b(?:incomplete application|apply now to|start your application)\b'
            ],
            subject_weight=30,
            body_weight=40,
            priority=50
        ),

        # 6. WITHDRAWAL
        ClassificationRule(
            name="withdrawal_family",
            category=RuleCategory.WITHDRAWAL,
            subject_patterns=[
                r'\b(?:application withdrawn|withdrawal confirmation|candidacy withdrawn)\b'
            ],
            body_patterns=[
                r'\b(?:withdrawn your application|confirmed withdrawal|no longer under consideration per your request)\b'
            ],
            negative_patterns=[],
            subject_weight=35,
            body_weight=40,
            priority=60
        ),

        # 7. RECRUITER CONTACT
        ClassificationRule(
            name="recruiter_contact_family",
            category=RuleCategory.RECRUITER_CONTACT,
            subject_patterns=[
                r'\b(?:came across your profile|new opportunity|exciting role at|job opportunity)\b'
            ],
            body_patterns=[
                r'\b(?:came across your profile|impressed by your background|exciting role at)\b',
                r'\b(?:would love to connect regarding|thought you might be a fit for)\b'
            ],
            negative_patterns=[],
            subject_weight=25,
            body_weight=35,
            priority=70
        ),

        # 8. UNDER REVIEW
        ClassificationRule(
            name="under_review_family",
            category=RuleCategory.UNDER_REVIEW,
            subject_patterns=[
                r'\b(?:application in review|application under review|update regarding your application)\b'
            ],
            body_patterns=[
                r'\b(?:application is currently under review|hiring team is reviewing your profile)\b',
                r'\b(?:under review by the hiring manager)\b'
            ],
            negative_patterns=[],
            subject_weight=25,
            body_weight=35,
            priority=80
        )
    ]

    @classmethod
    def evaluate(cls, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate an email against all structured rule families and return evidence assessment.

        Returns:
            Dict containing:
                - is_job_related: bool
                - confidence: float (0.0 to 1.0)
                - evidence_score: int (0 to 100)
                - category: RuleCategory
                - status: str (e.g. 'Interview', 'Rejected', 'Offer', 'Assessment', 'Applied')
                - event_type: str
                - company: str
                - job_title: str
                - is_deterministic_final: bool (True if score >= 70, bypassing AI)
                - rule_hits: List[str]
                - negative_hits: List[str]
        """
        subject = email_data.get('subject', '') or ''
        body = email_data.get('body', '') or email_data.get('snippet', '') or ''
        snippet = email_data.get('snippet', '') or ''
        sender = email_data.get('sender', '') or ''
        sender_domain = email_data.get('sender_domain', '') or cls._extract_domain(sender)
        combined_text = f"{subject} {snippet} {body}".lower()

        # Step 0: Check for obvious non-job digests, newsletters, or security alerts
        non_job_hits = []
        for pattern in cls.NON_JOB_PATTERNS:
            if re.search(pattern, combined_text, re.IGNORECASE):
                non_job_hits.append(pattern)

        # Extract entity heuristics
        company, job_title = cls._extract_entities(subject, sender, sender_domain, snippet)

        best_category = RuleCategory.OTHER
        best_score = 0
        best_rule_hits = []
        all_negative_hits = []

        # Evaluate against each classification rule
        for rule in cls.RULES:
            if not rule.enabled:
                continue

            current_score = 0
            current_hits = []

            # A. Check Negative Context first
            has_negative = False
            for neg_pat in rule.negative_patterns:
                if re.search(neg_pat, combined_text, re.IGNORECASE):
                    has_negative = True
                    all_negative_hits.append(f"{rule.name}: {neg_pat}")
                    break

            if has_negative:
                continue  # Skip this rule due to negative context match

            # B. Subject Pattern Match (+subject_weight)
            for sub_pat in rule.subject_patterns:
                if re.search(sub_pat, subject, re.IGNORECASE):
                    current_score += rule.subject_weight
                    current_hits.append(f"Subject: {sub_pat}")
                    break

            # C. Body Pattern Match (+body_weight)
            for body_pat in rule.body_patterns:
                if re.search(body_pat, combined_text, re.IGNORECASE):
                    current_score += rule.body_weight
                    current_hits.append(f"Body: {body_pat}")
                    break

            # D. Sender ATS / Platform Signals (+10)
            if sender_domain in cls.ATS_DOMAINS:
                current_score += 15
                current_hits.append(f"ATS domain: {sender_domain}")
            elif sender_domain in cls.GENERIC_JOB_PLATFORMS:
                current_score += 5
                current_hits.append(f"Platform domain: {sender_domain}")

            for prefix in cls.RECRUITER_SENDER_PATTERNS:
                if re.search(prefix, sender, re.IGNORECASE):
                    current_score += 10
                    current_hits.append(f"Sender prefix: {prefix}")
                    break

            # E. Company Extracted Bonus (+10)
            if company:
                current_score += 10
                current_hits.append(f"Company extracted: {company}")

            if current_score > best_score:
                best_score = current_score
                best_category = rule.category
                best_rule_hits = current_hits

        # Apply penalty for newsletter / non-job patterns if detected
        if non_job_hits and best_score < cls.HIGH_CONFIDENCE_THRESHOLD:
            best_score = max(0, best_score - 40)
            all_negative_hits.extend(non_job_hits)

        # Cap score between 0 and 100
        final_evidence_score = max(0, min(best_score, 100))
        normalized_confidence = round(final_evidence_score / 100.0, 2)
        is_job_related = final_evidence_score >= cls.MIN_JOB_EVIDENCE_THRESHOLD

        # Map category to standard application status and event type
        status_map = {
            RuleCategory.REJECTION: 'Rejected',
            RuleCategory.INTERVIEW: 'Interview',
            RuleCategory.ASSESSMENT: 'Assessment',
            RuleCategory.OFFER: 'Offer',
            RuleCategory.APPLICATION_RECEIVED: 'Applied',
            RuleCategory.WITHDRAWAL: 'Applied',
            RuleCategory.RECRUITER_CONTACT: 'Applied',
            RuleCategory.UNDER_REVIEW: 'Applied',
            RuleCategory.OTHER: 'Applied',
            RuleCategory.NON_JOB: 'Applied'
        }
        event_map = {
            RuleCategory.REJECTION: 'rejection',
            RuleCategory.INTERVIEW: 'interview_invitation',
            RuleCategory.ASSESSMENT: 'coding_assessment',
            RuleCategory.OFFER: 'offer',
            RuleCategory.APPLICATION_RECEIVED: 'application_received',
            RuleCategory.WITHDRAWAL: 'other',
            RuleCategory.RECRUITER_CONTACT: 'recruiter_outreach',
            RuleCategory.UNDER_REVIEW: 'application_status_update',
            RuleCategory.OTHER: 'other',
            RuleCategory.NON_JOB: 'other'
        }

        # Deterministic Final Decision Criteria:
        # 1. Evidence score >= 70
        # 2. Key category determined (Interview, Rejection, Offer, Assessment, Application Received)
        # 3. No unresolved negative hits
        is_deterministic_final = (
            final_evidence_score >= cls.HIGH_CONFIDENCE_THRESHOLD
            and best_category in [
                RuleCategory.REJECTION,
                RuleCategory.INTERVIEW,
                RuleCategory.ASSESSMENT,
                RuleCategory.OFFER,
                RuleCategory.APPLICATION_RECEIVED
            ]
            and not non_job_hits
        )

        return {
            'is_job_related': is_job_related,
            'confidence': normalized_confidence,
            'evidence_score': final_evidence_score,
            'category': best_category.value,
            'status': status_map.get(best_category, 'Applied'),
            'event_type': event_map.get(best_category, 'other'),
            'company': company,
            'job_title': job_title,
            'is_deterministic_final': is_deterministic_final,
            'rule_hits': best_rule_hits,
            'negative_hits': all_negative_hits
        }

    @classmethod
    def _extract_domain(cls, email_str: str) -> str:
        """Extract sender domain safely."""
        if not email_str:
            return ''
        try:
            if '@' in email_str:
                return email_str.split('@')[-1].split('>')[0].strip().lower()
            return ''
        except Exception:
            return ''

    @classmethod
    def _extract_entities(cls, subject: str, sender: str, sender_domain: str, snippet: str = '') -> Tuple[str, str]:
        """Extract company name and job title using domain and regex heuristics."""
        company = ''
        job_title = ''

        # Extract display name from sender (e.g. 'Morningstar Workday <...>' -> 'Morningstar Workday')
        display_name = ''
        if '<' in sender:
            display_name = sender.split('<')[0].strip(' "\'')
        elif '@' in sender:
            display_name = sender.split('@')[0].strip(' "\'')
        else:
            display_name = sender.strip(' "\'')

        # 1. ATS Sender display name extraction
        if display_name and any(d in (sender_domain or '') for d in cls.ATS_DOMAINS):
            cand = re.sub(
                r'\b(via|workday|greenhouse|lever|careers|jobs|recruiting|recruitment|team|notifications|no-?reply|talent|hiring|system|mailer|alerts?|support)\b.*$',
                '', display_name, flags=re.IGNORECASE
            ).strip(' -–—:|')
            if len(cand) >= 2 and not any(w in cand.lower() for w in ['donotreply', 'no-reply', 'noreply', 'mailer', 'system']):
                company = cand

        # 2. Domain-based company heuristic (if not generic ATS or platform)
        if not company and sender_domain and '.' in sender_domain:
            if sender_domain not in cls.ATS_DOMAINS and sender_domain not in cls.GENERIC_JOB_PLATFORMS:
                parts = sender_domain.split('.')
                if len(parts) >= 2:
                    main_part = parts[0] if parts[0] not in ['mail', 'email', 'notifications', 'careers', 'jobs', 'recruiting', 'talent', 'hiring'] else parts[1]
                    if len(main_part) > 2:
                        company = main_part.capitalize()

        # 3. Subject line pattern heuristics (e.g. 'Thank you for applying to Morningstar!' or 'Interview at Google')
        if not company or company.lower() in ['mail', 'jobs', 'careers', 'recruiting', 'talent', 'indeed apply']:
            match_co = re.search(r'(?:for|at|with|to|from)\s+([A-Z0-9][A-Za-z0-9\s&.\'-]+?)(?:\s+(?:for|at|with|to|from)|\s*[-–—:|!]|[\(\[].*?[\)\]]|\s*$)', subject)
            if match_co:
                cand = match_co.group(1).strip(' !.,:;-–—')
                if 1 < len(cand) < 40 and not any(w in cand.lower() for w in ['interview', 'application', 'your', 'update', 'opportunity', 'invitation', 'assessment', 'status', 'position', 'role']):
                    company = cand

        # 4. Body / Snippet pattern heuristic (e.g. 'application was sent to Zepto' or 'Thank you for applying to ...')
        if not company or company.lower() in ['indeed apply', 'recruitment', 'talent']:
            body_co = re.search(r'(?:sent to|applying to|applied to|interest in)\s+([A-Z0-9][A-Za-z0-9\s&.\'-]+?)(?:\s+(?:for|at|with|to|from)|\s*[-–—:|!.,]|\s*$)', snippet)
            if body_co:
                cand = body_co.group(1).strip(' !.,:;-–—')
                if 1 < len(cand) < 40 and not any(w in cand.lower() for w in ['interview', 'application', 'your', 'update', 'opportunity', 'this role']):
                    company = cand

        # 5. Fallback to display name if company still empty
        if not company and display_name:
            cand = re.sub(
                r'\b(careers|jobs|recruiting|recruitment|team|notifications|no-?reply|talent|hiring|system|mailer|alerts?|support)\b.*$',
                '', display_name, flags=re.IGNORECASE
            ).strip(' -–—:|')
            if len(cand) >= 2 and not any(w in cand.lower() for w in ['donotreply', 'no-reply', 'noreply', 'mailer', 'system']):
                company = cand

        # 6. Extract Job Title
        match_role = re.search(r'(?:role|position|job):\s*([A-Za-z0-9\s\-/]+)', subject, re.IGNORECASE)
        if match_role:
            job_title = match_role.group(1).strip(' !.,:;-–—')
        elif 'indeed application:' in subject.lower():
            # e.g., "Indeed Application: AI Engineer Intern"
            job_title = subject.split(':')[-1].strip(' !.,:;-–—')
        else:
            match_role_2 = re.search(r'\b([A-Za-z\s]+?(?:Engineer|Developer|Analyst|Scientist|Manager|Intern|Architect|Consultant|Specialist|Associate))\b', subject, re.IGNORECASE)
            if match_role_2:
                cand_title = match_role_2.group(1).strip(' !.,:;-–—')
                if 2 < len(cand_title) < 50:
                    job_title = cand_title

        return company, job_title
