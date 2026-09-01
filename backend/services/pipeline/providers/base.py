"""
Base Classifier Provider Abstract Interface for ApplyTrack AI.

Enforces a common interface across all AI providers (Hugging Face, Groq, Gemini, OpenRouter):
- Strict input normalization (minimum necessary context, zero attachments)
- Standardized structured JSON output
- Strict schema validation
- Provider cooldown & failure isolation
"""
import time
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

# Supported Application Status values
VALID_STATUSES = {'Applied', 'Under Review', 'Screening', 'Assessment', 'Interview', 'Offer', 'Rejected', 'Withdrawn', 'Unknown'}
VALID_EVENT_TYPES = {
    'application_received', 'application_confirmation', 'application_status_update',
    'interview_invitation', 'interview_scheduling', 'interview_confirmation',
    'coding_assessment', 'assessment_invitation', 'offer', 'rejection',
    'position_filled', 'candidate_not_selected', 'recruiter_outreach', 'other'
}


class BaseClassifierProvider(ABC):
    """
    Abstract base class for intelligence pipeline classification providers.
    """

    def __init__(self, name: str):
        self.name = name.lower()
        self._cooldown_until: float = 0.0

    @property
    def is_in_cooldown(self) -> bool:
        """Check if provider is temporarily cooled down due to errors or rate limits."""
        return time.time() < self._cooldown_until

    def trigger_cooldown(self, seconds: int = 60, reason: str = "") -> None:
        """Mark provider as in cooldown."""
        self._cooldown_until = time.time() + seconds
        logger.warning(f"Provider [{self.name}] cooldown activated for {seconds}s: {reason}")

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider API key and configuration are available."""
        pass

    @abstractmethod
    def classify(self, email_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute classification on minimal email context.

        Returns:
            Structured dict or None on failure/unavailability:
            {
                'is_job_related': bool,
                'company': str,
                'job_title': str,
                'status': str,
                'event_type': str,
                'interview_date': Optional[str],
                'confidence': float (0.0 to 1.0),
                'reasoning': str,
                'provider': str
            }
        """
        pass

    def prepare_prompt(self, email_data: Dict[str, Any]) -> str:
        """
        Build minimal, focused prompt without huge threads or attachments.
        """
        subject = (email_data.get('subject') or '')[:200]
        sender = (email_data.get('sender') or '')[:150]
        snippet = (email_data.get('snippet') or '')[:300]
        body = (email_data.get('body') or snippet)[:1500]  # Bounded to 1500 chars

        prompt = f"""You are an expert AI classifying emails for an automated Job Application Tracker.
Analyze the following email and return ONLY a valid JSON object.

EMAIL METADATA:
From: {sender}
Subject: {subject}
Content:
{body}

RESPONSE REQUIREMENTS:
Return ONLY valid JSON matching this schema:
{{
  "is_job_related": boolean,
  "company": string (extracted company name, or empty string if not found),
  "job_title": string (extracted job title, or empty string if not found),
  "status": string (one of: "Applied", "Under Review", "Screening", "Assessment", "Interview", "Offer", "Rejected", "Withdrawn", "Unknown"),
  "event_type": string (one of: "application_received", "interview_invitation", "coding_assessment", "offer", "rejection", "recruiter_outreach", "application_status_update", "other"),
  "interview_date": string or null (ISO-8601 date string if an interview date is explicitly scheduled, otherwise null),
  "confidence": number between 0.0 and 1.0,
  "reasoning": string (brief 1-sentence rationale)
}}"""
        return prompt

    def validate_and_normalize(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Validate and normalize raw LLM dictionary response.
        Enforces strict enum and confidence bounds.
        """
        if not isinstance(raw_data, dict):
            return None

        is_job = bool(raw_data.get('is_job_related', False))
        company = str(raw_data.get('company') or '').strip()
        job_title = str(raw_data.get('job_title') or '').strip()
        status = str(raw_data.get('status') or 'Applied').strip()
        event_type = str(raw_data.get('event_type') or 'other').strip().lower()
        interview_date = raw_data.get('interview_date')
        reasoning = str(raw_data.get('reasoning') or '').strip()

        try:
            confidence = float(raw_data.get('confidence', 0.5))
            confidence = max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            confidence = 0.5

        # Normalize status to valid enum choice
        if status not in VALID_STATUSES:
            # Map common variants
            status_lower = status.lower()
            if 'interview' in status_lower:
                status = 'Interview'
            elif 'reject' in status_lower:
                status = 'Rejected'
            elif 'offer' in status_lower:
                status = 'Offer'
            elif 'assess' in status_lower or 'test' in status_lower:
                status = 'Assessment'
            elif 'applied' in status_lower or 'received' in status_lower:
                status = 'Applied'
            elif 'review' in status_lower:
                status = 'Under Review'
            else:
                status = 'Unknown'

        # Normalize event type
        if event_type not in VALID_EVENT_TYPES:
            event_type = 'other'

        return {
            'is_job_related': is_job,
            'company': company,
            'job_title': job_title,
            'status': status,
            'event_type': event_type,
            'interview_date': interview_date,
            'confidence': confidence,
            'reasoning': reasoning,
            'provider': self.name
        }

    def parse_json_safely(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract and parse JSON object from LLM response text."""
        if not text:
            return None
        text = text.strip()
        
        # Strip markdown code fences if present
        if text.startswith('```json'):
            text = text[7:]
        elif text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
        text = text.strip()

        try:
            data = json.loads(text)
            return self.validate_and_normalize(data)
        except json.JSONDecodeError:
            # Try finding first { and last }
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1 and end > start:
                try:
                    data = json.loads(text[start:end+1])
                    return self.validate_and_normalize(data)
                except Exception as e:
                    logger.warning(f"Provider [{self.name}] failed JSON substring parse: {e}")
            return None
