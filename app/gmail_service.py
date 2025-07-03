import base64
import email
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from sqlalchemy.orm import Session
from app.models import User, EmailProcessingLog
from app.config import settings

class GmailService:
    def __init__(self, credentials: Credentials):
        self.service = build('gmail', 'v1', credentials=credentials)
    
    def get_messages_since_date(self, since_date: datetime, max_results: int = 500) -> List[Dict[str, Any]]:
        """Get messages since a specific date"""
        try:
            # Format date for Gmail API query
            date_str = since_date.strftime('%Y/%m/%d')
            query = f'after:{date_str}'
            
            # Get message list
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            # Get full message details
            full_messages = []
            for message in messages:
                try:
                    msg = self.service.users().messages().get(
                        userId='me',
                        id=message['id'],
                        format='full'
                    ).execute()
                    full_messages.append(msg)
                except HttpError as e:
                    print(f"Error fetching message {message['id']}: {e}")
                    continue
            
            return full_messages
            
        except HttpError as error:
            print(f"An error occurred: {error}")
            return []
    
    def get_new_messages(self, last_check: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get messages received since last check"""
        if last_check is None:
            last_check = datetime.utcnow() - timedelta(days=settings.initial_days_to_scan)
        
        return self.get_messages_since_date(last_check)
    
    def extract_email_content(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant content from Gmail message"""
        headers = message['payload'].get('headers', [])
        
        # Extract headers
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
        date_header = next((h['value'] for h in headers if h['name'] == 'Date'), '')
        
        # Parse date
        try:
            import email.utils
            date_tuple = email.utils.parsedate_tz(date_header)
            if date_tuple:
                timestamp = email.utils.mktime_tz(date_tuple)
                email_date = datetime.fromtimestamp(timestamp)
            else:
                email_date = datetime.utcnow()
        except:
            email_date = datetime.utcnow()
        
        # Extract body
        body = self._get_message_body(message['payload'])
        
        return {
            'id': message['id'],
            'subject': subject,
            'sender': sender,
            'date': email_date,
            'body': body,
            'snippet': message.get('snippet', ''),
            'thread_id': message.get('threadId', '')
        }
    
    def _get_message_body(self, payload: Dict[str, Any]) -> str:
        """Extract body text from message payload"""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data')
                    if data:
                        body += base64.urlsafe_b64decode(data).decode('utf-8')
                elif part['mimeType'] == 'text/html':
                    data = part['body'].get('data')
                    if data and not body:  # Use HTML if no plain text
                        body += base64.urlsafe_b64decode(data).decode('utf-8')
                elif 'parts' in part:
                    body += self._get_message_body(part)
        else:
            if payload['mimeType'] == 'text/plain':
                data = payload['body'].get('data')
                if data:
                    body += base64.urlsafe_b64decode(data).decode('utf-8')
        
        return body
    
    def is_package_related_email(self, email_content: Dict[str, Any]) -> bool:
        """Simple heuristic to determine if email might be package-related"""
        text_to_check = f"{email_content['subject']} {email_content['body']} {email_content['snippet']}".lower()
        
        package_keywords = [
            'tracking', 'shipment', 'delivered', 'delivery', 'package', 'order',
            'shipped', 'ups', 'fedex', 'usps', 'dhl', 'amazon', 'tracking number',
            'out for delivery', 'in transit', 'estimated delivery', 'dispatch',
            'shipping confirmation', 'order confirmation', 'tracking information'
        ]
        
        return any(keyword in text_to_check for keyword in package_keywords)

def get_user_gmail_service(user: User, db: Session) -> Optional[GmailService]:
    """Get Gmail service for a user with credential refresh"""
    from app.auth import refresh_user_credentials
    
    credentials = refresh_user_credentials(user, db)
    if not credentials:
        return None
    
    return GmailService(credentials)

def mark_email_processed(user_id: int, email_id: str, success: bool, 
                        error_message: Optional[str], processing_time: Optional[int],
                        db: Session):
    """Mark an email as processed to avoid reprocessing"""
    log = EmailProcessingLog(
        user_id=user_id,
        email_id=email_id,
        success=success,
        error_message=error_message,
        processing_time_ms=processing_time
    )
    db.add(log)
    try:
        db.commit()
    except:
        db.rollback()  # Ignore duplicates

def is_email_already_processed(user_id: int, email_id: str, db: Session) -> bool:
    """Check if email has already been processed"""
    return db.query(EmailProcessingLog).filter(
        EmailProcessingLog.user_id == user_id,
        EmailProcessingLog.email_id == email_id
    ).first() is not None