"""
Hugging Face Inference Service for ApplyTrack AI.

Provides fast zero-shot and classification inference for job email categorization
before routing to more expensive/slower LLM fallback providers.
"""
import logging
import requests
from typing import Dict, Any, Optional, List
from django.conf import settings

logger = logging.getLogger(__name__)


class HFService:
    """
    Service client for Hugging Face Serverless Inference API.
    """

    DEFAULT_MODEL = "facebook/bart-large-mnli"
    API_URL_TEMPLATE = "https://api-inference.huggingface.co/models/{model}"

    CANDIDATE_LABELS = [
        "job interview invitation",
        "job offer letter",
        "job application received confirmation",
        "technical coding assessment",
        "job application rejection",
        "marketing newsletter or generic job alert",
        "not job related"
    ]

    @classmethod
    def classify_email_zero_shot(cls, text: str, labels: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Run zero-shot classification on email text using Hugging Face inference.

        Returns:
            Dict with 'top_label', 'score', and 'all_scores', or None if unavailable/failed.
        """
        api_key = getattr(settings, 'HF_TOKEN', '') or getattr(settings, 'HUGGINGFACE_API_KEY', '')
        if not api_key:
            logger.debug("HF_TOKEN / HUGGINGFACE_API_KEY not configured. Skipping HF tier.")
            return None

        model_name = getattr(settings, 'HF_MODEL_NAME', cls.DEFAULT_MODEL)
        url = cls.API_URL_TEMPLATE.format(model=model_name)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # Truncate text for performance & token limits
        truncated_text = text[:1500] if text else ""
        candidate_labels = labels or cls.CANDIDATE_LABELS

        payload = {
            "inputs": truncated_text,
            "parameters": {
                "candidate_labels": candidate_labels,
                "multi_label": False
            }
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=12)
            if response.status_code == 200:
                data = response.json()
                scores = data.get('scores', [])
                returned_labels = data.get('labels', [])
                if scores and returned_labels:
                    top_label = returned_labels[0]
                    top_score = float(scores[0])
                    return {
                        'top_label': top_label,
                        'score': top_score,
                        'all_scores': dict(zip(returned_labels, scores)),
                        'model': model_name
                    }
            elif response.status_code == 503:
                # Model is loading
                logger.info(f"Hugging Face model {model_name} is currently loading.")
                return None
            else:
                logger.warning(f"Hugging Face API returned status {response.status_code}: {response.text[:200]}")
                return None
        except Exception as e:
            logger.warning(f"Hugging Face inference request failed: {str(e)}")
            return None
