"""
Canonical Email Object & Compression Module for ApplyTrack AI.

This module enforces strict data structures for ingested emails:
- Extracts only required fields and safe metadata
- Strictly ignores and excludes all attachments (PDF, DOCX, XLSX, images, ZIP, etc.)
- Serializes and compresses (lossless gzip) the canonical payload for storage in Cloudflare R2
- Computes SHA-256 digests for payload integrity verification
- Generates structured R2 object reference keys
"""
import gzip
import json
import hashlib
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from django.utils import timezone

logger = logging.getLogger(__name__)


class CanonicalEmail:
    """
    Structured, normalized representation of an ingested Gmail email message.
    Strictly excludes attachments.
    """

    SCHEMA_VERSION = "1.0"
    COMPRESSION_VERSION = "gzip-v1"

    def __init__(
        self,
        gmail_message_id: str,
        thread_id: str,
        sender: str,
        sender_domain: str,
        recipient: str,
        subject: str,
        received_at: str,
        labels: Optional[List[str]] = None,
        snippet: str = "",
        plain_text_content: str = "",
        safe_metadata: Optional[Dict[str, Any]] = None,
        ingested_at: Optional[str] = None,
    ):
        self.gmail_message_id = gmail_message_id
        self.thread_id = thread_id
        self.sender = sender
        self.sender_domain = sender_domain
        self.recipient = recipient
        self.subject = subject
        self.received_at = received_at
        self.labels = labels or []
        self.snippet = snippet
        self.plain_text_content = plain_text_content
        self.safe_metadata = safe_metadata or {}
        self.ingested_at = ingested_at or timezone.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert canonical email to a clean dictionary payload."""
        return {
            "version": self.SCHEMA_VERSION,
            "gmail_message_id": self.gmail_message_id,
            "thread_id": self.thread_id,
            "sender": self.sender,
            "sender_domain": self.sender_domain,
            "recipient": self.recipient,
            "subject": self.subject,
            "received_at": self.received_at,
            "labels": self.labels,
            "snippet": self.snippet,
            "plain_text_content": self.plain_text_content,
            "safe_metadata": self.safe_metadata,
            "ingested_at": self.ingested_at,
            # Explicit confirmation that attachments are omitted
            "attachments_omitted": True,
        }

    def compute_sha256(self) -> str:
        """Compute SHA-256 hex digest of the canonical JSON representation."""
        json_bytes = json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, default=str).encode('utf-8')
        return hashlib.sha256(json_bytes).hexdigest()

    def to_compressed_bytes(self) -> bytes:
        """
        Serialize canonical dictionary to JSON and compress using gzip.
        Returns compressed bytes.
        """
        json_str = json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, default=str)
        return gzip.compress(json_str.encode('utf-8'))

    def to_compressed_payload(self) -> Tuple[bytes, str, int]:
        """
        Serialize and compress canonical email.
        Returns:
            Tuple of (compressed_bytes, content_sha256, compressed_size_bytes)
        """
        compressed = self.to_compressed_bytes()
        sha256_hash = self.compute_sha256()
        return compressed, sha256_hash, len(compressed)

    @classmethod
    def from_compressed_bytes(cls, compressed_bytes: bytes) -> 'CanonicalEmail':
        """Decompress gzip bytes and reconstruct a CanonicalEmail instance losslessly."""
        decompressed_str = gzip.decompress(compressed_bytes).decode('utf-8')
        data = json.loads(decompressed_str)
        return cls(
            gmail_message_id=data.get('gmail_message_id', ''),
            thread_id=data.get('thread_id', ''),
            sender=data.get('sender', ''),
            sender_domain=data.get('sender_domain', ''),
            recipient=data.get('recipient', ''),
            subject=data.get('subject', ''),
            received_at=data.get('received_at', ''),
            labels=data.get('labels', []),
            snippet=data.get('snippet', ''),
            plain_text_content=data.get('plain_text_content', ''),
            safe_metadata=data.get('safe_metadata', {}),
            ingested_at=data.get('ingested_at'),
        )

    @staticmethod
    def generate_object_key(user_id: int | str, received_dt: Optional[datetime], message_id: str) -> str:
        """
        Generate standard Backblaze B2 / Object Storage key path:
        users/{user_id}/emails/{YYYY}/{MM}/{message_id}.json.gz
        """
        dt = received_dt or timezone.now()
        year = dt.strftime('%Y')
        month = dt.strftime('%m')
        safe_msg_id = str(message_id).strip().replace('/', '_')
        return f"users/{user_id}/emails/{year}/{month}/{safe_msg_id}.json.gz"

    generate_b2_key = generate_object_key
    generate_r2_key = generate_object_key

    @classmethod
    def from_raw_gmail_message(cls, raw_msg: Dict[str, Any], parsed_info: Dict[str, Any]) -> 'CanonicalEmail':
        """
        Factory method to construct a CanonicalEmail from raw Gmail API output
        and parsed headers/body, strictly discarding all attachment binaries.
        """
        headers = raw_msg.get('payload', {}).get('headers', [])
        header_map = {h.get('name', '').lower(): h.get('value', '') for h in headers if isinstance(h, dict)}

        msg_id = raw_msg.get('id', '')
        thread_id = raw_msg.get('threadId', '')
        labels = raw_msg.get('labelIds', [])
        snippet = raw_msg.get('snippet', '')
        
        sender = parsed_info.get('sender') or header_map.get('from', '')
        sender_domain = parsed_info.get('sender_domain') or ''
        recipient = header_map.get('to', '')
        subject = parsed_info.get('subject') or header_map.get('subject', 'No Subject')
        
        received_at_dt = parsed_info.get('received_at')
        if received_at_dt and hasattr(received_at_dt, 'isoformat'):
            received_at_str = received_at_dt.isoformat()
        else:
            received_at_str = timezone.now().isoformat()

        body_plain = parsed_info.get('body') or snippet

        # Safe metadata only (message-id header, references, in-reply-to, history_id)
        # Binary attachments are NOT extracted or retained.
        safe_metadata = {
            'message_id_header': header_map.get('message-id', ''),
            'in_reply_to': header_map.get('in-reply-to', ''),
            'references': header_map.get('references', ''),
            'history_id': str(raw_msg.get('historyId', '')),
        }

        return cls(
            gmail_message_id=msg_id,
            thread_id=thread_id,
            sender=sender,
            sender_domain=sender_domain,
            recipient=recipient,
            subject=subject,
            received_at=received_at_str,
            labels=labels,
            snippet=snippet,
            plain_text_content=body_plain,
            safe_metadata=safe_metadata,
        )
