"""
Groq LLM Classification Provider for ApplyTrack AI.

Primary LLM fallback provider using fast inference models (default: llama-3.3-70b-versatile).
Enforces structured JSON output and strict validation.
"""
import logging
import requests
from typing import Dict, Any, Optional
from django.conf import settings
from .base import BaseClassifierProvider

logger = logging.getLogger(__name__)


class GroqProvider(BaseClassifierProvider):
    """
    Tier 3 Primary LLM Provider: Groq API.
    """

    def __init__(self):
        super().__init__(name="groq")

    def is_available(self) -> bool:
        api_key = getattr(settings, 'GROQ_API_KEY', '')
        return bool(api_key) and not self.is_in_cooldown

    def classify(self, email_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.is_available():
            return None

        api_key = getattr(settings, 'GROQ_API_KEY', '')
        model = getattr(settings, 'GROQ_MODEL', 'llama-3.3-70b-versatile')
        timeout = getattr(settings, 'AI_PROVIDER_TIMEOUT_SECONDS', 15)

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        prompt = self.prepare_prompt(email_data)
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a specialized JSON-only classifier for job application emails."},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": 500
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            from ..rate_limiter import ProviderRateLimiter
            ProviderRateLimiter.update_from_headers(self.name, resp.headers)

            if resp.status_code == 200:
                data = resp.json()
                content = data['choices'][0]['message']['content']
                return self.parse_json_safely(content)
            elif resp.status_code == 429:
                retry_after = resp.headers.get('retry-after') or resp.headers.get('Retry-After')
                delay = int(retry_after) if (retry_after and retry_after.isdigit()) else 60
                self.trigger_cooldown(seconds=delay, reason=f"Groq rate limited (429, Retry-After: {delay}s)")
            else:
                logger.warning(f"Groq API error HTTP {resp.status_code}: {resp.text[:200]}")
                if resp.status_code in [500, 502, 503, 504]:
                    self.trigger_cooldown(seconds=30, reason=f"Groq server error ({resp.status_code})")
        except requests.exceptions.Timeout:
            logger.warning("Groq API request timed out")
            self.trigger_cooldown(seconds=30, reason="Timeout")
        except Exception as e:
            logger.warning(f"Groq API unexpected error: {str(e)}")

        return None
