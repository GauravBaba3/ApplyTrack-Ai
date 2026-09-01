"""
Multi-Provider LLM Fallback Service for ApplyTrack AI.

Orchestrates LLM inference across modular provider implementations:
Groq -> Google Gemini -> OpenRouter -> Human Review.
Iterates through configured providers with automatic failover, timeout protection, and cooldown management.
"""
import logging
from typing import Dict, Any, Optional
from django.conf import settings
from .providers.registry import ProviderRegistry

logger = logging.getLogger(__name__)


class LLMFallbackService:
    """
    Orchestrates LLM inference across configurable provider implementations.
    """

    @classmethod
    def classify_email(cls, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify job email and extract structured data using the configured LLM provider cascade.

        Iterates through available providers according to settings.AI_PROVIDER_ORDER:
        (Default: Groq -> Gemini -> OpenRouter)
        """
        chain = ProviderRegistry.get_configured_llm_chain()

        for provider in chain:
            if not provider.is_available():
                continue

            try:
                from .provider_manager import ProviderManager
                res = ProviderManager.execute_call(provider, email_data)
                if res and res.get('is_job_related') is not None:
                    res['provider'] = provider.name
                    logger.debug(f"LLM Classification succeeded via provider [{provider.name}]")
                    return res
            except Exception as e:
                logger.warning(f"Provider [{provider.name}] error during classification: {str(e)}")
                provider.trigger_cooldown(seconds=30, reason=f"Classification exception: {str(e)[:100]}")

        # If all providers fail or are unconfigured, return conservative defaults for Human Review
        logger.info("All configured LLM providers exhausted or unavailable. Routing to Human Review.")
        return {
            'is_job_related': False,
            'confidence': 0.0,
            'company': '',
            'job_title': '',
            'status': 'Applied',
            'event_type': 'other',
            'interview_date': None,
            'provider': 'none',
            'error': 'All LLM providers exhausted or unconfigured',
            'needs_review': True
        }

    # Backward compatibility helper methods for test mocking
    @classmethod
    def _call_groq(cls, prompt: str, api_key: str) -> Optional[Dict[str, Any]]:
        groq_provider = ProviderRegistry.get_provider('groq')
        if groq_provider:
            return groq_provider.classify({'body': prompt})
        return None

    @classmethod
    def _call_gemini(cls, prompt: str, api_key: str) -> Optional[Dict[str, Any]]:
        gemini_provider = ProviderRegistry.get_provider('gemini')
        if gemini_provider:
            return gemini_provider.classify({'body': prompt})
        return None

    @classmethod
    def _call_openrouter(cls, prompt: str, api_key: str) -> Optional[Dict[str, Any]]:
        openrouter_provider = ProviderRegistry.get_provider('openrouter')
        if openrouter_provider:
            return openrouter_provider.classify({'body': prompt})
        return None
