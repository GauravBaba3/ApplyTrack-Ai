"""
Triage Service for ApplyTrack AI.

Fast, lightweight deterministic classifier for assigning incoming emails
into high-recall priority queues:
- P1 (High): Interview invitations, interview scheduling, job offers,
            important application decisions, rejection / selection decisions that need timely tracking.
- P2 (Medium): Coding challenges / assessments, application acknowledgments,
              application status updates, recruiter communications, follow-ups.
- P3 (Low): Generic job alerts, newsletters, weekly digests, low-confidence items,
            items intentionally deferred for later re-triage.

Crucial Principle:
P3 items are NEVER permanently discarded; they are queued into P3 for deferred processing.
"""
import re
import logging
from typing import Dict, Any, Tuple
from django.utils import timezone

logger = logging.getLogger(__name__)


class TriageStatus:
    JOB_LIKELY = 'job_likely'
    UNCERTAIN = 'uncertain'
    LOW_PRIORITY = 'low_priority'


class TriageService:
    """
    High-recall triage classifier determining priority queue (P1, P2, P3) and triage status.
    """

    # P1: Timely decision-making actions (Interviews, Offers, Direct Decisions, Rejections)
    P1_PATTERNS = [
        r'\binterview\b',
        r'\bschedule\b',
        r'\boffer\b',
        r'\bcongratulations\b',
        r'\btechnical round\b',
        r'\bphone screen\b',
        r'\bzoom\b',
        r'\bgoogle meet\b',
        r'\bteams meeting\b',
        r'\binvitation to interview\b',
        r'\bavailable for a chat\b',
        r'\bdiscuss your application\b',
        r'\bunfortunately\b',
        r'\bregret to inform\b',
        r'\bnot selected\b',
        r'\bother candidates\b',
        r'\bposition filled\b',
        r'\bposition closed\b',
        r'\bdecision on your application\b',
    ]

    # P2: Assessments, Application Receipts, Recruiter Status Updates
    P2_PATTERNS = [
        r'\bcoding assessment\b',
        r'\bhackerrank\b',
        r'\bleetcode\b',
        r'\bcodility\b',
        r'\btake-home\b',
        r'\bthank you for applying\b',
        r'\bapplication received\b',
        r'\bwe received your application\b',
        r'\bapplication confirmation\b',
        r'\bapplication confirmed\b',
        r'\bapplication submitted\b',
        r'\bstatus update\b',
        r'\bunder review\b',
        r'\bin review\b',
        r'\bapplication for\b',
        r'\brecruiter\b',
        r'\bhiring team\b',
    ]

    # P3: Low-priority Marketing, Generic Alerts, Newsletters, Deferred items
    P3_PATTERNS = [
        r'\bjob alert\b',
        r'\bweekly digest\b',
        r'\brecommended jobs\b',
        r'\bnew opportunities\b',
        r'\bnewsletter\b',
        r'\btop jobs\b',
        r'\bjobs you may like\b',
        r'\bdaily job\b',
        r'\bjob recommendations\b',
    ]

    @classmethod
    def determine_priority(cls, email_data: Dict[str, Any]) -> Tuple[str, str]:
        """
        Classify email into priority queue (P1, P2, P3) based on subject, snippet, and sender.

        Returns:
            Tuple of (priority: 'P1'|'P2'|'P3', reason: str)
        """
        triage_dict = cls.triage_email(email_data)
        return triage_dict['priority'], triage_dict['triage_reason']

    @classmethod
    def triage_email(cls, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive lightweight high-recall triage.

        Returns:
            Dict containing:
            - priority: 'P1' | 'P2' | 'P3'
            - triage_status: 'job_likely' | 'uncertain' | 'low_priority'
            - triage_score: float (0.0 to 1.0)
            - triage_reason: str
            - triaged_at: datetime
        """
        subject = (email_data.get('subject') or '').lower()
        snippet = (email_data.get('snippet') or '').lower()
        sender = (email_data.get('sender') or '').lower()
        event_type = (email_data.get('event_type') or '').lower()
        text = f"{subject} {snippet}"

        now = timezone.now()

        # 1. Event type checks (if already detected or hints available)
        if any(p1_event in event_type for p1_event in [
            'interview', 'offer', 'scheduling', 'recruiter_outreach',
            'rejection', 'position_filled', 'candidate_not_selected'
        ]):
            return {
                'priority': 'P1',
                'triage_status': TriageStatus.JOB_LIKELY,
                'triage_score': 0.95,
                'triage_reason': f"Matched P1 event type: {event_type}",
                'triaged_at': now
            }

        if any(p2_event in event_type for p2_event in [
            'assessment', 'coding', 'application_received', 'application_confirmation', 'status_update'
        ]):
            return {
                'priority': 'P2',
                'triage_status': TriageStatus.JOB_LIKELY,
                'triage_score': 0.80,
                'triage_reason': f"Matched P2 event type: {event_type}",
                'triaged_at': now
            }

        if any(p3_event in event_type for p3_event in ['newsletter', 'alert', 'digest']):
            return {
                'priority': 'P3',
                'triage_status': TriageStatus.LOW_PRIORITY,
                'triage_score': 0.20,
                'triage_reason': f"Matched P3 newsletter/alert type: {event_type}",
                'triaged_at': now
            }

        # 2. Check P3 (Newsletters / Job Alerts)
        for pattern in cls.P3_PATTERNS:
            if re.search(pattern, subject) or re.search(pattern, text):
                return {
                    'priority': 'P3',
                    'triage_status': TriageStatus.LOW_PRIORITY,
                    'triage_score': 0.25,
                    'triage_reason': f"Matched low priority/alert pattern: {pattern}",
                    'triaged_at': now
                }

        # 3. Check P1 (Interviews, Offers, Rejections)
        for pattern in cls.P1_PATTERNS:
            if re.search(pattern, subject):
                return {
                    'priority': 'P1',
                    'triage_status': TriageStatus.JOB_LIKELY,
                    'triage_score': 0.90,
                    'triage_reason': f"Subject matched high priority P1 pattern: {pattern}",
                    'triaged_at': now
                }

        for pattern in cls.P1_PATTERNS:
            if re.search(pattern, text):
                return {
                    'priority': 'P1',
                    'triage_status': TriageStatus.JOB_LIKELY,
                    'triage_score': 0.85,
                    'triage_reason': f"Content matched high priority P1 pattern: {pattern}",
                    'triaged_at': now
                }

        # 4. Check P2 (Assessments, Status Updates, Receipts)
        for pattern in cls.P2_PATTERNS:
            if re.search(pattern, subject):
                return {
                    'priority': 'P2',
                    'triage_status': TriageStatus.JOB_LIKELY,
                    'triage_score': 0.75,
                    'triage_reason': f"Subject matched medium priority P2 pattern: {pattern}",
                    'triaged_at': now
                }

        for pattern in cls.P2_PATTERNS:
            if re.search(pattern, text):
                return {
                    'priority': 'P2',
                    'triage_status': TriageStatus.JOB_LIKELY,
                    'triage_score': 0.70,
                    'triage_reason': f"Content matched medium priority P2 pattern: {pattern}",
                    'triaged_at': now
                }

        # 5. Domain / Recruiter hints
        recruiter_keywords = ['careers', 'jobs', 'recruiting', 'talent', 'hr', 'greenhouse', 'lever', 'workday']
        if any(kw in sender for kw in recruiter_keywords):
            return {
                'priority': 'P2',
                'triage_status': TriageStatus.UNCERTAIN,
                'triage_score': 0.55,
                'triage_reason': "Sender address contains recruiter/ATS keywords",
                'triaged_at': now
            }

        # Default fallback is P3 (Uncertain / Low priority deferred for rescanning)
        return {
            'priority': 'P3',
            'triage_status': TriageStatus.UNCERTAIN,
            'triage_score': 0.35,
            'triage_reason': "No explicit job keywords matched; queued into P3 for deferred processing",
            'triaged_at': now
        }
