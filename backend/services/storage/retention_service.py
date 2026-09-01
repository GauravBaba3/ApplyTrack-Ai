"""
Raw Email Retention Management Service for ApplyTrack AI.

Enforces configurable retention lifecycles for raw canonical email objects
stored in Backblaze B2:
- Default retention target: 90 days (3 months)
- Prunes expired raw .json.gz blobs from Backblaze B2
- Updates object storage status to 'pruned' in Neon PostgreSQL
- Retains all structured application metadata, history, classifications,
  and relational tracking records permanently in Neon PostgreSQL
"""
import logging
from typing import Dict, Any, List
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

from apps.gmail_integration.models import ProcessedEmail, R2StorageStatus
from .b2_service import B2StorageService, StorageStatus

logger = logging.getLogger(__name__)


class RetentionService:
    """
    Service managing lifecycle and retention pruning of raw email objects in Backblaze B2.
    """

    @classmethod
    def calculate_expiration_date(cls, received_at=None, retention_days=None) -> timezone.datetime:
        """
        Calculate raw object expiration date based on received timestamp and retention window.
        """
        base_dt = received_at or timezone.now()
        days = retention_days if retention_days is not None else getattr(settings, 'RAW_EMAIL_RETENTION_DAYS', 90)
        return base_dt + timedelta(days=days)

    @classmethod
    def prune_expired_raw_objects(cls, dry_run: bool = False, limit: int = 500) -> Dict[str, Any]:
        """
        Identify and prune raw .json.gz objects in Backblaze B2 that have passed raw_retention_expires_at.

        Args:
            dry_run: If True, only identify objects without deleting them.
            limit: Maximum number of records to process per invocation.

        Returns:
            Summary dict of processed, pruned, failed, and skipped items.
        """
        now = timezone.now()
        expired_qs = ProcessedEmail.objects.filter(
            raw_retention_expires_at__lte=now,
            r2_storage_status=StorageStatus.UPLOADED,
            r2_object_key__isnull=False
        ).exclude(r2_object_key='').order_by('raw_retention_expires_at')[:limit]

        total_found = expired_qs.count()
        pruned_count = 0
        failed_count = 0

        logger.info(f"Retention audit found {total_found} expired raw email objects (dry_run={dry_run}).")

        if dry_run:
            return {
                'dry_run': True,
                'expired_found': total_found,
                'pruned': 0,
                'failed': 0,
                'message': f"Dry run: {total_found} raw email objects are eligible for pruning."
            }

        for email in expired_qs:
            try:
                object_key = email.r2_object_key
                # Delete from Backblaze B2
                deleted = B2StorageService.delete_object(object_key)
                if deleted:
                    email.r2_storage_status = StorageStatus.PRUNED
                    email.save(update_fields=['r2_storage_status'])
                    pruned_count += 1
                else:
                    failed_count += 1
                    logger.warning(f"Failed to delete Backblaze B2 object key '{object_key}' for ProcessedEmail {email.id}")
            except Exception as e:
                failed_count += 1
                logger.error(f"Error during retention pruning of email {email.id}: {str(e)}")

        logger.info(f"Retention pruning completed: {pruned_count} pruned, {failed_count} failed out of {total_found}.")
        return {
            'dry_run': False,
            'expired_found': total_found,
            'pruned': pruned_count,
            'failed': failed_count,
            'message': f"Successfully pruned {pruned_count} expired raw email objects."
        }
