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

    @classmethod
    def extract_entities(cls, email_data):
        """
        Extract company and job title heuristics from email subject, sender, and snippet.
        """
        subject = email_data.get('subject', '')
        sender = email_data.get('sender', '')
        sender_domain = cls._extract_domain(sender)
        
        company = ''
        job_title = ''
        
        # 1. Company heuristic: domain name (if not generic platform)
        if sender_domain and sender_domain not in cls.RECRUITER_DOMAINS and '.' in sender_domain:
            parts = sender_domain.split('.')
            if len(parts) >= 2 and parts[0] not in ['mail', 'email', 'notifications', 'careers', 'jobs', 'recruiting']:
                company = parts[0].capitalize()
            elif len(parts) >= 3 and parts[0] in ['careers', 'jobs', 'recruiting']:
                company = parts[1].capitalize()

        # 2. Company / Title heuristic from common subject patterns
        # e.g., "Interview with Stripe: Software Engineer" or "Application Received: Senior Dev at Google"
        match_at = re.search(r'(?:for|at|with)\s+([A-Z][A-Za-z0-9\s&]+?)(?:\s+for|\s+at|\s+with|\s*[-–—:|]|\s*$)', subject)
        if match_at and not company:
            candidate_co = match_at.group(1).strip()
            if len(candidate_co) > 1 and len(candidate_co) < 40:
                company = candidate_co

        match_role = re.search(r'(?:role|position|job):\s*([A-Za-z0-9\s\-/]+)', subject, re.IGNORECASE)
        if match_role:
            job_title = match_role.group(1).strip()

        return company, job_title

    @classmethod
    def extract_status(cls, email_data):
        """Extract application status heuristic from subject and snippet."""
        text = f"{email_data.get('subject', '')} {email_data.get('snippet', '')}".lower()
        if any(w in text for w in ['offer', 'congratulations']):
            return 'Offer'
        elif any(w in text for w in ['interview', 'schedule', 'technical round', 'phone screen']):
            return 'Interview'
        elif any(w in text for w in ['assessment', 'test', 'coding challenge', 'hackerrank']):
            return 'Assessment'
        elif any(w in text for w in ['unfortunately', 'not selected', 'regret to inform', 'position filled']):
            return 'Rejected'
        return 'Applied'

    @classmethod
    def extract_event_type(cls, email_data):
        """Extract event type heuristic from subject and snippet."""
        text = f"{email_data.get('subject', '')} {email_data.get('snippet', '')}".lower()
        if any(w in text for w in ['interview', 'invitation to interview', 'schedule']):
            return 'interview_invitation'
        elif any(w in text for w in ['offer', 'congratulations']):
            return 'offer'
        elif any(w in text for w in ['assessment', 'coding test', 'hackerrank']):
            return 'coding_assessment'
        elif any(w in text for w in ['unfortunately', 'regret', 'not selected']):
            return 'rejection'
        elif any(w in text for w in ['application received', 'thank you for applying']):
            return 'application_received'
        return 'other'

