"""
Provider Registry & Cascade Manager for ApplyTrack AI.

Instantiates and manages the lifecycle of all classification providers:
- Hugging Face Zero-Shot
- Groq LLM
- Google Gemini LLM
- OpenRouter LLM
Resolves LLM providers in configurable order (default: Groq -> Gemini -> OpenRouter).
"""
import logging
from typing import List, Dict, Any, Optional
from django.conf import settings

from .base import BaseClassifierProvider
from .huggingface_provider import HuggingFaceProvider
from .groq_provider import GroqProvider
from .gemini_provider import GeminiProvider
from .openrouter_provider import OpenRouterProvider

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """
    Registry and factory for AI classification providers.
    """

    _providers: Dict[str, BaseClassifierProvider] = {}
    _initialized: bool = False

    @classmethod
    def initialize(cls) -> None:
        """Initialize provider singletons."""
        if not cls._initialized:
            cls._providers = {
                'huggingface': HuggingFaceProvider(),
                'groq': GroqProvider(),
                'gemini': GeminiProvider(),
                'openrouter': OpenRouterProvider(),
            }
            cls._initialized = True

    @classmethod
    def get_provider(cls, name: str) -> Optional[BaseClassifierProvider]:
        """Get provider instance by name."""
        cls.initialize()
        return cls._providers.get(name.lower())

    @classmethod
    def get_configured_llm_chain(cls) -> List[BaseClassifierProvider]:
        """
        Get ordered list of available LLM fallback providers based on AI_PROVIDER_ORDER setting.
        """
        cls.initialize()
        order_names = getattr(settings, 'AI_PROVIDER_ORDER', ['groq', 'gemini', 'openrouter'])
        chain = []
        for name in order_names:
            provider = cls._providers.get(name.lower())
            if provider and provider.is_available():
                chain.append(provider)
        return chain

    @classmethod
    def get_all_llm_providers(cls) -> List[BaseClassifierProvider]:
        """Get all instantiated LLM providers in fallback order."""
        cls.initialize()
        order_names = getattr(settings, 'AI_PROVIDER_ORDER', ['groq', 'gemini', 'openrouter'])
        chain = []
        for name in order_names:
            provider = cls._providers.get(name.lower())
            if provider:
                chain.append(provider)
        return chain

    @classmethod
    def reset(cls) -> None:
        """Reset registry (for test suites)."""
        cls._initialized = False
        cls._providers = {}
