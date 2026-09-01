"""
Backblaze B2 Cloud Object Storage Service for ApplyTrack AI.

Backblaze B2 provides S3-compatible object storage used to store compressed
canonical email payloads securely and durably. Neon PostgreSQL maintains
relational indices, structured metadata, and object reference keys.
"""
import logging
from typing import Optional, Dict, Any, List
from django.conf import settings
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, BotoCoreError

logger = logging.getLogger(__name__)


class StorageStatus:
    PENDING = 'pending'
    UPLOADED = 'uploaded'
    FAILED = 'failed'
    PRUNED = 'pruned'


# Backward compatibility alias
R2StorageStatus = StorageStatus


class B2StorageService:
    """
    Service client for Backblaze B2 Cloud Object Storage (S3-compatible API).
    """

    _client = None

    @classmethod
    def reset_client(cls) -> None:
        """Reset cached boto3 client (useful in tests/reconfigurations)."""
        cls._client = None

    @classmethod
    def get_client(cls):
        """Lazy initialization of boto3 S3 client for Backblaze B2."""
        if cls._client is not None:
            return cls._client

        key_id = (
            getattr(settings, 'B2_KEY_ID', '') or
            getattr(settings, 'R2_ACCESS_KEY_ID', '')
        )
        app_key = (
            getattr(settings, 'B2_APPLICATION_KEY', '') or
            getattr(settings, 'R2_SECRET_ACCESS_KEY', '')
        )
        endpoint_url = (
            getattr(settings, 'B2_ENDPOINT_URL', '') or
            getattr(settings, 'R2_ENDPOINT_URL', '')
        )
        region_name = getattr(settings, 'B2_REGION', 'auto')

        if not (key_id and app_key and endpoint_url):
            logger.warning(
                "Backblaze B2 credentials (B2_KEY_ID, B2_APPLICATION_KEY, "
                "or B2_ENDPOINT_URL) not fully configured in settings."
            )
            return None

        try:
            cls._client = boto3.client(
                's3',
                endpoint_url=endpoint_url,
                aws_access_key_id=key_id,
                aws_secret_access_key=app_key,
                config=Config(
                    signature_version='s3v4',
                    retries={'max_attempts': 3, 'mode': 'standard'},
                    connect_timeout=10,
                    read_timeout=30,
                ),
                region_name=region_name
            )
            return cls._client
        except Exception as e:
            logger.error(f"Failed to initialize Backblaze B2 boto3 client: {str(e)}")
            return None

    @classmethod
    def get_bucket_name(cls) -> str:
        """Get the configured Backblaze B2 bucket name."""
        return (
            getattr(settings, 'B2_BUCKET_NAME', '') or
            getattr(settings, 'R2_BUCKET_NAME', 'applytrack-ai-emails')
        )

    @classmethod
    def is_configured(cls) -> bool:
        """Check if Backblaze B2 credentials and client are available."""
        return cls.get_client() is not None

    @classmethod
    def upload_compressed_email(
        cls,
        object_key: str,
        data_bytes: bytes,
        sha256_hash: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Upload compressed canonical email bytes to Backblaze B2 object storage.

        Args:
            object_key: Target object key (e.g., users/{user_id}/emails/{year}/{month}/{msg_id}.json.gz)
            data_bytes: Compressed raw bytes
            sha256_hash: Optional SHA-256 checksum for integrity tracking
            metadata: Optional S3 metadata dictionary

        Returns:
            bool indicating success
        """
        client = cls.get_client()
        bucket = cls.get_bucket_name()

        if client is None:
            logger.info(
                f"[B2 Mock/Dev Mode] B2 not configured. Skipping remote upload of key: {object_key} "
                f"({len(data_bytes)} bytes)"
            )
            return True  # Graceful fallback during dev/testing when B2 credentials are unset

        try:
            extra_args = {
                'ContentType': 'application/json',
                'ContentEncoding': 'gzip',
            }
            s3_meta = {}
            if sha256_hash:
                s3_meta['sha256'] = str(sha256_hash)
            if metadata:
                s3_meta.update({k: str(v) for k, v in metadata.items()})

            if s3_meta:
                extra_args['Metadata'] = s3_meta

            client.put_object(
                Bucket=bucket,
                Key=object_key,
                Body=data_bytes,
                **extra_args
            )
            logger.info(f"Successfully uploaded {len(data_bytes)} bytes to Backblaze B2 object key: {object_key}")
            return True

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Backblaze B2 upload error for key '{object_key}': {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error uploading to Backblaze B2 '{object_key}': {str(e)}")
            return False

    @classmethod
    def download_compressed_email(cls, object_key: str) -> Optional[bytes]:
        """
        Download compressed canonical email bytes from Backblaze B2.

        Args:
            object_key: Object key to download

        Returns:
            bytes or None if not found/error
        """
        client = cls.get_client()
        bucket = cls.get_bucket_name()

        if client is None:
            logger.warning(f"[B2 Mock/Dev Mode] B2 not configured. Cannot download key: {object_key}")
            return None

        try:
            response = client.get_object(Bucket=bucket, Key=object_key)
            body_stream = response.get('Body')
            if body_stream:
                return body_stream.read()
            return None
        except ClientError as e:
            if e.response.get('Error', {}).get('Code') == 'NoSuchKey':
                logger.warning(f"Backblaze B2 key not found: {object_key}")
            else:
                logger.error(f"Backblaze B2 download ClientError for key '{object_key}': {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading from Backblaze B2 '{object_key}': {str(e)}")
            return None

    @classmethod
    def object_exists(cls, object_key: str) -> bool:
        """Check if an object exists in Backblaze B2."""
        client = cls.get_client()
        bucket = cls.get_bucket_name()

        if client is None:
            return False

        try:
            client.head_object(Bucket=bucket, Key=object_key)
            return True
        except ClientError as e:
            if e.response.get('Error', {}).get('Code') in ('404', 'NoSuchKey'):
                return False
            logger.error(f"Error checking Backblaze B2 object existence for key '{object_key}': {str(e)}")
            return False
        except Exception:
            return False

    @classmethod
    def delete_object(cls, object_key: str) -> bool:
        """Delete an object from Backblaze B2."""
        client = cls.get_client()
        bucket = cls.get_bucket_name()

        if client is None:
            return True

        try:
            client.delete_object(Bucket=bucket, Key=object_key)
            logger.info(f"Deleted Backblaze B2 object key: {object_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete Backblaze B2 object '{object_key}': {str(e)}")
            return False
