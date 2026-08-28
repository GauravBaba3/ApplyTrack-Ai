"""
Application matcher for matching emails to existing applications.
"""
import logging
from difflib import SequenceMatcher
from django.utils import timezone

from apps.applications.models import Application, ApplicationStatus
from apps.gmail_integration.models import ProcessedEmail

logger = logging.getLogger(__name__)


class ApplicationMatcher:
    """Service for matching emails to applications."""
    
    @classmethod
    def match_email_to_application(cls, email_data, user):
        """
        Match an email to an existing application or determine if it's a new one.
        
        Args:
            email_data: Dictionary with email information
            user: User model instance
            
        Returns:
            Tuple of (application: Application or None, confidence: float, is_new: bool)
        """
        try:
            company = email_data.get('company', '')
            job_title = email_data.get('job_title', '')
            sender = email_data.get('sender', '')
            sender_domain = email_data.get('sender_domain', '')
            subject = email_data.get('subject', '')
            thread_id = email_data.get('thread_id', '')
            
            # Get all applications for this user
            applications = Application.objects.filter(user=user)
            
            best_match = None
            best_score = 0.0
            
            for app in applications:
                score = cls._calculate_match_score(
                    app, company, job_title, sender, sender_domain, subject, thread_id
                )
                
                if score > best_score:
                    best_score = score
                    best_match = app
            
            # If we have a good match to an existing application, return it
            if best_match and best_score >= 0.5:
                return best_match, best_score, False
            
            # Determine if this is a new application (has company or job_title and no existing match)
            is_new = best_score < 0.5 and bool(company or job_title)
            
            if is_new:
                # Use the confidence of the classification extraction
                new_confidence = email_data.get('confidence', 0.8)
                return None, new_confidence, True
            
            # No match and not a new application
            return None, best_score, False
            
        except Exception as e:
            logger.error(f"Application matching failed: {str(e)}")
            return None, 0.0, False
    
    @classmethod
    def _calculate_match_score(cls, application, company, job_title, sender, sender_domain, subject, thread_id):
        """Calculate match score between an application and email data."""
        score = 0.0
        
        # Company match (strong signal)
        if company and application.company:
            company_similarity = cls._text_similarity(company.lower(), application.company.lower())
            if company_similarity >= 0.8:
                score += 0.4
            elif company_similarity >= 0.6:
                score += 0.2
            else:
                score += company_similarity * 0.3
        
        # Job title match (strong signal)
        if job_title and application.job_title:
            title_similarity = cls._text_similarity(job_title.lower(), application.job_title.lower())
            if title_similarity >= 0.8:
                score += 0.3
            elif title_similarity >= 0.6:
                score += 0.15
            else:
                score += title_similarity * 0.2
        
        # Sender domain match (medium signal)
        if sender_domain and application.company:
            company_domain = cls._extract_domain_from_company(application.company)
            if company_domain and sender_domain == company_domain:
                score += 0.2
            elif sender_domain in application.company.lower():
                score += 0.15
        
        # Subject match (medium signal)
        if subject and application.company:
            if application.company.lower() in subject.lower():
                score += 0.15
        
        if subject and application.job_title:
            if application.job_title.lower() in subject.lower():
                score += 0.1
        
        # Thread match (very strong signal)
        # Check if this thread is already associated with this application
        if thread_id:
            existing_emails = ProcessedEmail.objects.filter(
                application_id=application.id,
                thread_id=thread_id
            )
            if existing_emails.exists():
                score += 0.5  # Very strong signal
        
        # Clamp score
        return min(score, 1.0)
    
    @classmethod
    def _text_similarity(cls, a, b):
        """Calculate text similarity using SequenceMatcher."""
        return SequenceMatcher(None, a, b).ratio()
    
    @classmethod
    def _extract_domain_from_company(cls, company):
        """Extract domain from company name if it contains one."""
        # Common patterns: "Company (company.com)", "Company - company.com", etc.
        import re
        
        # Look for domain patterns
        patterns = [
            r'\(([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\)',  # (domain.com)
            r'\s*-\s*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',  # - domain.com
            r'\s+at\s+([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',  # at domain.com
        ]
        
        for pattern in patterns:
            match = re.search(pattern, company)
            if match:
                return match.group(1).lower()
        
        return None
    
    @classmethod
    def create_application_from_email(cls, email_data, user):
        """
        Create a new application from email data.
        
        Args:
            email_data: Dictionary with email information
            user: User model instance
            
        Returns:
            Application model instance
        """
        try:
            company = email_data.get('company', 'Unknown')
            job_title = email_data.get('job_title', 'Unknown')
            received_at = email_data.get('received_at')
            
            # Determine application date (use email date if no better info)
            application_date = received_at.date() if received_at else timezone.now().date()
            
            # Determine initial status
            detected_status = email_data.get('detected_status', ApplicationStatus.APPLIED)
            
            application = Application.objects.create(
                user=user,
                company=company,
                job_title=job_title,
                application_date=application_date,
                current_status=detected_status,
                is_ai_detected=True,
                is_manual=False,
                confidence=email_data.get('confidence', 0.7),
                needs_review=email_data.get('confidence', 0.0) < 0.7
            )
            
            return application
            
        except Exception as e:
            logger.error(f"Failed to create application from email: {str(e)}")
            raise
