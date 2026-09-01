"""
Gmail API service for fetching and processing emails.
"""
import logging
import base64
import re
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport import requests

logger = logging.getLogger(__name__)


class GmailService:
    """Service for interacting with Gmail API."""
    
    def __init__(self, user):
        """Initialize Gmail service for a user."""
        self.user = user
        self.credentials = None
        self.service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Gmail API service with user credentials."""
        try:
            if not self.user.gmail_connected:
                raise Exception("Gmail is not connected for this user")
            
            # Create credentials from stored tokens
            self.credentials = Credentials(
                token=self.user.gmail_access_token,
                refresh_token=self.user.gmail_refresh_token,
                token_uri='https://oauth2.googleapis.com/token',
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                scopes=['https://www.googleapis.com/auth/gmail.readonly']
            )
            
            # Refresh token if expired or invalid
            if not self.credentials.valid:
                self.credentials.refresh(requests.Request())
                # Update user's token
                self.user.gmail_access_token = self.credentials.token
                if self.credentials.expiry:
                    expiry_dt = self.credentials.expiry
                    if timezone.is_naive(expiry_dt):
                        expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
                    self.user.gmail_token_expiry = expiry_dt
                self.user.save(update_fields=['gmail_access_token', 'gmail_token_expiry'])
            
            # Build Gmail service
            self.service = build('gmail', 'v1', credentials=self.credentials)
            
        except Exception as e:
            logger.error(f"Failed to initialize Gmail service: {str(e)}")
            raise
    
    def get_message_page(self, page_token=None, max_results=25, days_back=30, after_timestamp=None):
        """
        Fetch a single page of message identifiers from Gmail using nextPageToken.
        
        Args:
            page_token: Optional nextPageToken from previous page
            max_results: Batch size
            days_back: Historical days window if after_timestamp is not specified
            after_timestamp: Optional datetime to query messages newer than this time
            
        Returns:
            Tuple of (list_of_message_stubs, next_page_token)
        """
        try:
            if not self.service:
                raise Exception("Gmail service not initialized")
            
            # Calculate date for filtering
            if after_timestamp:
                # Query messages received after the last sync timestamp
                date_filter = after_timestamp.strftime('%Y/%m/%d')
            else:
                date_filter = (timezone.now() - timedelta(days=days_back)).strftime('%Y/%m/%d')
            
            # Broad, high-recall date filter (no premature keyword restriction)
            query = f'after:{date_filter}'
            
            list_kwargs = {
                'userId': 'me',
                'q': query,
                'maxResults': max_results
            }
            if page_token:
                list_kwargs['pageToken'] = page_token
            
            results = self.service.users().messages().list(**list_kwargs).execute()
            messages = results.get('messages', [])
            next_page_token = results.get('nextPageToken')
            
            # If no messages found, terminate pagination
            if not messages:
                return [], None
            
            return messages, next_page_token
            
        except HttpError as e:
            logger.error(f"Gmail API error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to fetch message page: {str(e)}")
            raise
    
    def fetch_and_parse_message(self, message_id):
        """Fetch full details for a single message and parse it."""
        try:
            if not self.service:
                raise Exception("Gmail service not initialized")
            
            msg = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            return self._parse_message(msg)
        except Exception as e:
            logger.warning(f"Failed to fetch details for message {message_id}: {str(e)}")
            return None

    def get_recent_messages(self, max_results=50, days_back=30):
        """Backward-compatible helper to fetch and parse recent messages."""
        messages, _ = self.get_message_page(max_results=max_results, days_back=days_back)
        full_messages = []
        for m in messages:
            parsed = self.fetch_and_parse_message(m['id'])
            if parsed:
                full_messages.append(parsed)
        return full_messages
    
    def _parse_message(self, message):
        """Parse Gmail message into structured format."""
        try:
            headers = message.get('payload', {}).get('headers', [])
            header_dict = {h['name'].lower(): h['value'] for h in headers}
            
            # Extract basic info
            msg_id = message.get('id')
            thread_id = message.get('threadId')
            snippet = message.get('snippet', '')
            
            # Extract sender
            sender = header_dict.get('from', '')
            sender_domain = self._extract_domain(sender)
            
            # Extract subject
            subject = header_dict.get('subject', 'No Subject')
            
            # Extract date
            date_str = header_dict.get('date', '')
            received_at = self._parse_date(date_str)
            
            # Extract body
            body = self._extract_body(message)
            
            return {
                'gmail_message_id': msg_id,
                'thread_id': thread_id,
                'sender': sender,
                'sender_domain': sender_domain,
                'subject': subject,
                'received_at': received_at,
                'snippet': snippet,
                'body': body or snippet,
                'raw': message
            }
            
        except Exception as e:
            logger.error(f"Failed to parse message: {str(e)}")
            return None
    
    def _extract_domain(self, email):
        """Extract domain from email address."""
        try:
            if '@' in email:
                clean_email = email.split('<')[-1].split('>')[0].strip()
                return clean_email.split('@')[-1].lower()
            return ''
        except:
            return ''
    
    def _parse_date(self, date_str):
        """Parse email date string into datetime."""
        try:
            date_str = date_str.strip()
            
            # Try parsing with different formats
            for fmt in [
                '%a, %d %b %Y %H:%M:%S %z',
                '%a, %d %b %Y %H:%M:%S %Z',
                '%d %b %Y %H:%M:%S %z',
                '%d %b %Y %H:%M:%S %Z',
                '%a, %d %b %Y %H:%M:%S',
            ]:
                try:
                    dt = datetime.strptime(date_str.split(' (')[0], fmt)
                    if timezone.is_naive(dt):
                        return timezone.make_aware(dt)
                    return dt
                except ValueError:
                    continue
            
            # Fallback to now
            return timezone.now()
            
        except Exception:
            return timezone.now()
    
    def _extract_body(self, message):
        """Extract plain text or HTML body recursively from message."""
        try:
            payload = message.get('payload', {})
            text_parts = []
            html_parts = []

            def walk_parts(part):
                mime_type = part.get('mimeType', '')
                body_data = part.get('body', {}).get('data', '')
                
                if body_data:
                    decoded = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                    if mime_type == 'text/plain':
                        text_parts.append(decoded)
                    elif mime_type == 'text/html':
                        html_parts.append(decoded)

                for subpart in part.get('parts', []):
                    walk_parts(subpart)

            walk_parts(payload)

            if text_parts:
                return '\n'.join(text_parts).strip()

            if html_parts:
                # Strip HTML tags
                raw_html = '\n'.join(html_parts)
                clean_text = re.sub(r'<[^>]+>', ' ', raw_html)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                return clean_text

            return ''
            
        except Exception as e:
            logger.warning(f"Error extracting body: {str(e)}")
            return ''
    
    def get_message_by_id(self, message_id):
        """Get a specific message by ID."""
        try:
            if not self.service:
                raise Exception("Gmail service not initialized")
            
            msg = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            return self._parse_message(msg)
            
        except Exception as e:
            logger.error(f"Failed to get message {message_id}: {str(e)}")
            return None
