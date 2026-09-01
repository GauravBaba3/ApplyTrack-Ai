"""
Provider-Neutral Object Storage Service for ApplyTrack AI.

Delegates canonical email payload storage, retrieval, and deletion to the configured
cloud object storage provider (Default: Backblaze B2 S3-compatible storage).
"""
import logging
from typing import Optional, Dict, Any
from .b2_service import B2StorageService, StorageStatus

logger = logging.getLogger(__name__)


class ObjectStorageService:
    """
    Provider-neutral interface for cloud object storage operations.
    """

    _provider = B2StorageService

    @classmethod
    def set_provider(cls, provider_cls):
        """Allow dynamic provider overrides (useful for testing)."""
        cls._provider = provider_cls

    @classmethod
    def is_configured(cls) -> bool:
        """Check if underlying object storage provider is configured."""
        return cls._provider.is_configured()

    @classmethod
    def get_bucket_name(cls) -> str:
        """Get configured bucket name from provider."""
        return cls._provider.get_bucket_name()

    @classmethod
    def upload_compressed_email(
        cls,
        object_key: str,
        data_bytes: bytes,
        sha256_hash: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """Upload compressed email to object storage."""
        return cls._provider.upload_compressed_email(
            object_key=object_key,
            data_bytes=data_bytes,
            sha256_hash=sha256_hash,
            metadata=metadata
        )

    @classmethod
    def download_compressed_email(cls, object_key: str) -> Optional[bytes]:
        """Download compressed email from object storage."""
        return cls._provider.download_compressed_email(object_key=object_key)

    @classmethod
    def object_exists(cls, object_key: str) -> bool:
        """Check if object exists in object storage."""
        return cls._provider.object_exists(object_key=object_key)

    @classmethod
    def delete_object(cls, object_key: str) -> bool:
        """Delete object from object storage."""
        return cls._provider.delete_object(object_key=object_key)
