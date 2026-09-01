"""
Google Gemini Classification Provider for ApplyTrack AI.

Tier 3 Secondary LLM Provider (default: gemini-1.5-flash).
Produces structured JSON classification when Groq is unavailable.
"""
import logging
import requests
from typing import Dict, Any, Optional
from django.conf import settings
from .base import BaseClassifierProvider

logger = logging.getLogger(__name__)


class GeminiProvider(BaseClassifierProvider):
    """
    Tier 3 Secondary LLM Provider: Google Gemini API.
    """

    def __init__(self):
        super().__init__(name="gemini")

    def is_available(self) -> bool:
        api_key = getattr(settings, 'GEMINI_API_KEY', '')
        return bool(api_key) and not self.is_in_cooldown

    def classify(self, email_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.is_available():
            return None

        api_key = getattr(settings, 'GEMINI_API_KEY', '')
        model = getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash')
        timeout = getattr(settings, 'AI_PROVIDER_TIMEOUT_SECONDS', 15)

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}

        prompt = self.prepare_prompt(email_data)
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
                "maxOutputTokens": 500
            }
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            from ..rate_limiter import ProviderRateLimiter
            ProviderRateLimiter.update_from_headers(self.name, resp.headers)

            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get('candidates', [])
                if candidates and 'content' in candidates[0]:
                    parts = candidates[0]['content'].get('parts', [])
                    if parts:
                        text = parts[0].get('text', '')
                        return self.parse_json_safely(text)
            elif resp.status_code == 429:
                retry_after = resp.headers.get('retry-after') or resp.headers.get('Retry-After')
                delay = int(retry_after) if (retry_after and retry_after.isdigit()) else 60
                self.trigger_cooldown(seconds=delay, reason=f"Gemini rate limited (429, Retry-After: {delay}s)")
            else:
                logger.warning(f"Gemini API error HTTP {resp.status_code}: {resp.text[:200]}")
                if resp.status_code in [500, 502, 503, 504]:
                    self.trigger_cooldown(seconds=30, reason=f"Gemini server error ({resp.status_code})")
        except requests.exceptions.Timeout:
            logger.warning("Gemini API request timed out")
            self.trigger_cooldown(seconds=30, reason="Timeout")
        except Exception as e:
            logger.warning(f"Gemini API unexpected error: {str(e)}")

        return None
