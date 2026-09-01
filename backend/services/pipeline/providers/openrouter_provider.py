"""
OpenRouter LLM Classification Provider for ApplyTrack AI.

Tier 3 Tertiary Fallback LLM Provider (default: meta-llama/llama-3.3-70b-instruct).
Ensures classification capability if Groq and Gemini are unavailable.
"""
import logging
import requests
from typing import Dict, Any, Optional
from django.conf import settings
from .base import BaseClassifierProvider

logger = logging.getLogger(__name__)


class OpenRouterProvider(BaseClassifierProvider):
    """
    Tier 3 Tertiary LLM Provider: OpenRouter API.
    """

    def __init__(self):
        super().__init__(name="openrouter")

    def is_available(self) -> bool:
        api_key = getattr(settings, 'OPENROUTER_API_KEY', '')
        return bool(api_key) and not self.is_in_cooldown

    def classify(self, email_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.is_available():
            return None

        api_key = getattr(settings, 'OPENROUTER_API_KEY', '')
        model = getattr(settings, 'OPENROUTER_MODEL', 'meta-llama/llama-3.3-70b-instruct')
        timeout = min(6, getattr(settings, 'AI_PROVIDER_TIMEOUT_SECONDS', 6))

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://applytrack.ai",
            "X-Title": "ApplyTrack AI",
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
                self.trigger_cooldown(seconds=delay, reason=f"OpenRouter rate limited (429, Retry-After: {delay}s)")
            else:
                logger.warning(f"OpenRouter API error HTTP {resp.status_code}: {resp.text[:200]}")
                self.trigger_cooldown(seconds=60, reason=f"OpenRouter error ({resp.status_code})")
        except requests.exceptions.Timeout:
            logger.warning("OpenRouter API request timed out")
            self.trigger_cooldown(seconds=30, reason="Timeout")
        except Exception as e:
            logger.warning(f"OpenRouter API unexpected error: {str(e)}")

        return None
