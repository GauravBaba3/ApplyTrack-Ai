"""
Hugging Face Zero-Shot Classification Provider for ApplyTrack AI.

Uses Hugging Face Inference API with configurable model (default: facebook/bart-large-mnli).
Treats output score as model evidence, not mathematical probability.
"""
import logging
import requests
from typing import Dict, Any, Optional
from django.conf import settings
from .base import BaseClassifierProvider

logger = logging.getLogger(__name__)


class HuggingFaceProvider(BaseClassifierProvider):
    """
    Tier 2: Zero-Shot Hugging Face inference classification provider.
    """

    CANDIDATE_LABELS = [
        "job interview invitation",
        "job application rejection",
        "job offer letter",
        "technical coding assessment",
        "job application received confirmation",
        "recruiter outreach message",
        "not job related"
    ]

    LABEL_TO_STATUS = {
        "job interview invitation": ("Interview", "interview_invitation", True),
        "job application rejection": ("Rejected", "rejection", True),
        "job offer letter": ("Offer", "offer", True),
        "technical coding assessment": ("Assessment", "coding_assessment", True),
        "job application received confirmation": ("Applied", "application_received", True),
        "recruiter outreach message": ("Applied", "recruiter_outreach", True),
        "not job related": ("Unknown", "other", False),
    }

    def __init__(self):
        super().__init__(name="huggingface")

    def is_available(self) -> bool:
        token = getattr(settings, 'HF_TOKEN', '') or getattr(settings, 'HUGGINGFACE_API_KEY', '')
        return bool(token) and not self.is_in_cooldown

    def classify(self, email_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.is_available():
            return None

        token = getattr(settings, 'HF_TOKEN', '') or getattr(settings, 'HUGGINGFACE_API_KEY', '')
        model_name = getattr(settings, 'HF_MODEL_NAME', 'facebook/bart-large-mnli')
        timeout = getattr(settings, 'AI_PROVIDER_TIMEOUT_SECONDS', 15)

        api_url = f"https://api-inference.huggingface.co/models/{model_name}"
        headers = {"Authorization": f"Bearer {token}"}

        subject = email_data.get('subject', '') or ''
        snippet = email_data.get('snippet', '') or ''
        text = f"{subject} {snippet}".strip()[:500]

        payload = {
            "inputs": text,
            "parameters": {
                "candidate_labels": self.CANDIDATE_LABELS,
                "multi_label": False
            }
        }

        try:
            resp = requests.post(api_url, headers=headers, json=payload, timeout=timeout)
            from ..rate_limiter import ProviderRateLimiter
            ProviderRateLimiter.update_from_headers(self.name, resp.headers)

            if resp.status_code == 200:
                result = resp.json()
                labels = result.get('labels', [])
                scores = result.get('scores', [])
                if labels and scores:
                    top_label = labels[0]
                    top_score = float(scores[0])
                    status, event_type, is_job = self.LABEL_TO_STATUS.get(top_label, ("Applied", "other", True))
                    return {
                        'is_job_related': is_job,
                        'company': '',
                        'job_title': '',
                        'status': status,
                        'event_type': event_type,
                        'interview_date': None,
                        'confidence': top_score,
                        'reasoning': f"HF Zero-shot model ({model_name}) classified as '{top_label}' with evidence score {top_score:.2f}",
                        'provider': self.name,
                        'top_label': top_label
                    }
            elif resp.status_code == 429:
                self.trigger_cooldown(seconds=60, reason="Hugging Face rate limited (429)")
            else:
                logger.warning(f"Hugging Face API returned status {resp.status_code}: {resp.text[:200]}")
                if resp.status_code in [500, 502, 503, 504]:
                    self.trigger_cooldown(seconds=30, reason=f"HF server error ({resp.status_code})")
        except requests.exceptions.Timeout:
            logger.warning("Hugging Face API request timed out")
            self.trigger_cooldown(seconds=30, reason="Timeout")
        except Exception as e:
            logger.warning(f"Hugging Face classification error: {str(e)}")

        return None
