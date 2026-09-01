"""
Cloudflare R2 Compatibility Layer for ApplyTrack AI.

DEPRECATED: Cloudflare R2 has been migrated to Backblaze B2 Cloud Storage.
This module provides backward compatibility aliases redirecting all calls to B2StorageService.
"""
import logging
from .b2_service import B2StorageService, StorageStatus

logger = logging.getLogger(__name__)

# Backward compatibility aliases
R2StorageStatus = StorageStatus
R2StorageService = B2StorageService
