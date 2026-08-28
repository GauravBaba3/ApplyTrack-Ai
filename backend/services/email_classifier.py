"""
Rule-based email classifier for filtering before AI processing.
"""
import re
import logging
from datetime import datetime, timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)


class EmailClassifier:
    """Rule-based classifier for filtering job-related emails."""
    
    # Keywords that indicate job-related emails
    JOB_KEYWORDS = [
        # Application related
        'application', 'apply', 'applied', 'candidate', 'applicant', 'referral',
        
        # Interview related
        'interview', 'schedule', 'meeting', 'call', 'screening', 'preliminary',
        'technical interview', 'phone screen', 'onsite', 'round', 'virtual interview',
        'video call', 'zoom', 'teams', 'google meet', 'invitation', 'invite',
        
        # Assessment related
        'assessment', 'test', 'exercise', 'challenge', 'task',
        'coding test', 'take-home', 'hackerrank', 'leetcode', 'codility',
        
        # Recruiter related
        'recruiter', 'talent', 'hiring', 'hr', 'talent acquisition',
        'recruitment', 'staffing', 'human resources', 'talent partner',
        
        # Job related
        'job', 'position', 'role', 'opening', 'opportunity',
        'career', 'careers', 'employment', 'analyst', 'engineer', 'developer',
        
        # Status related
        'status', 'update', 'next steps', 'proceed', 'shortlist', 'shortlisted',
        'moving forward', 'not moving forward', 'in review', 'under consideration',
        
        # Offer related
        'offer', 'congratulations', 'welcome', 'offer letter',
        'compensation', 'salary', 'benefits',
        
        # Rejection related
        'unfortunately', 'regret', 'not selected', 'other candidates',
        'not a fit', 'not moving', 'decided to move',
        'position filled', 'rejection', 'declined',
        
        # Withdrawal related
        'withdraw', 'no longer', 'cancel',
    ]
    
    # Domains that are likely from recruiters or job platforms
    RECRUITER_DOMAINS = [
        'linkedin.com', 'indeed.com', 'naukri.com',
        'monster.com', 'glassdoor.com', 'wellfound.com',
        'angel.co', 'hired.com', 'triplebyte.com',
        'jobvite.com', 'greenhouse.io', 'lever.co',
        'workday.com', 'icims.com', 'taleo.net',
    ]
    
    # Common job platform sender patterns
    JOB_PLATFORM_PATTERNS = [
        r'no-reply@',
        r'noreply@',
        r'notifications@',
        r'alerts@',
        r'jobs@',
        r'careers@',
        r'recruiting@',
        r'talent@',
        r'hr@',
    ]
    
    @classmethod
    def is_job_related(cls, email_data):
        """
        Determine if an email is likely job-related using rules.
        
        Args:
            email_data: Dictionary with sender, subject, snippet, body
            
        Returns:
            Tuple of (is_job_related: bool, confidence: float)
        """
        try:
            sender = email_data.get('sender', '').lower()
            subject = email_data.get('subject', '').lower()
            snippet = email_data.get('snippet', '').lower()
            body = email_data.get('body', '').lower()
            
            score = 0.0
            reasons = []
            
            # Check sender domain
            sender_domain = cls._extract_domain(sender)
            if sender_domain in cls.RECRUITER_DOMAINS:
                score += 0.4
                reasons.append(f"Sender domain: {sender_domain}")
            
            # Check sender pattern
            for pattern in cls.JOB_PLATFORM_PATTERNS:
                if re.search(pattern, sender):
                    score += 0.3
                    reasons.append(f"Sender pattern: {pattern}")
                    break
            
            # Check subject for keywords
            subject_keywords = cls._count_keywords(subject)
            if subject_keywords > 0:
                score += min(subject_keywords * 0.15, 0.3)
                reasons.append(f"Subject keywords: {subject_keywords}")
            
            # Check snippet for keywords
            snippet_keywords = cls._count_keywords(snippet)
            if snippet_keywords > 0:
                score += min(snippet_keywords * 0.1, 0.2)
                reasons.append(f"Snippet keywords: {snippet_keywords}")
            
            # Check body for keywords (less weight)
            body_keywords = cls._count_keywords(body)
            if body_keywords > 0:
                score += min(body_keywords * 0.05, 0.1)
                reasons.append(f"Body keywords: {body_keywords}")
            
            # Bonus for common job email phrases
            phrases = [
                'thank you for applying',
                'your application for',
                'we received your application',
                'application status',
                'interview invitation',
                'schedule an interview',
                'we would like to invite',
                'unfortunately we',
                'we regret to inform',
                'we are pleased to offer',
                'job offer',
                'next steps',
            ]
            
            for phrase in phrases:
                if phrase in subject or phrase in snippet or phrase in body:
                    score += 0.2
                    reasons.append(f"Phrase: {phrase}")
                    break
            
            # Clamp score
            score = min(score, 1.0)
            
            # Determine if job-related (conservative threshold)
            is_job_related = score >= 0.4
            
            logger.debug(f"Email classification: score={score:.2f}, reasons={reasons}")
            
            return is_job_related, score
            
        except Exception as e:
            logger.error(f"Email classification failed: {str(e)}")
            return False, 0.0
    
    @classmethod
    def _extract_domain(cls, email):
        """Extract domain from email address."""
        try:
            if '@' in email:
                return email.split('@')[-1].lower()
            return ''
        except:
            return ''
    
    @classmethod
    def _count_keywords(cls, text):
        """Count how many job keywords appear in text."""
        count = 0
        text_lower = text.lower()
        
        for keyword in cls.JOB_KEYWORDS:
            # Use word boundaries for whole word matching
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text_lower):
                count += 1
        
        return count
