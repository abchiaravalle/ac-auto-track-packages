import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from app.gmail_service import GmailService, get_user_gmail_service, mark_email_processed, is_email_already_processed
from app.models import EmailProcessingLog

@pytest.fixture
def mock_gmail_service():
    """Create a mock Gmail service"""
    with patch('app.gmail_service.build') as mock_build:
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        # Mock credentials
        mock_credentials = MagicMock()
        
        service = GmailService(mock_credentials)
        service.service = mock_service
        return service, mock_service

def test_gmail_service_initialization():
    """Test Gmail service initialization"""
    mock_credentials = MagicMock()
    
    with patch('app.gmail_service.build') as mock_build:
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        gmail_service = GmailService(mock_credentials)
        assert gmail_service.service == mock_service
        mock_build.assert_called_once_with('gmail', 'v1', credentials=mock_credentials)

def test_get_messages_since_date(mock_gmail_service):
    """Test getting messages since a specific date"""
    service, mock_service = mock_gmail_service
    
    # Mock Gmail API response
    mock_list_response = {
        'messages': [{'id': 'msg1'}, {'id': 'msg2'}]
    }
    mock_service.users().messages().list().execute.return_value = mock_list_response
    
    # Mock individual message responses
    mock_message = {
        'id': 'msg1',
        'payload': {
            'headers': [
                {'name': 'Subject', 'value': 'Test Subject'},
                {'name': 'From', 'value': 'test@example.com'},
                {'name': 'Date', 'value': 'Wed, 10 Jan 2024 10:00:00 +0000'}
            ],
            'mimeType': 'text/plain',
            'body': {'data': 'VGVzdCBtZXNzYWdl'}  # Base64 encoded "Test message"
        },
        'snippet': 'Test snippet'
    }
    mock_service.users().messages().get().execute.return_value = mock_message
    
    since_date = datetime.utcnow() - timedelta(days=1)
    messages = service.get_messages_since_date(since_date)
    
    assert len(messages) == 2
    mock_service.users().messages().list.assert_called_once()

def test_extract_email_content(mock_gmail_service):
    """Test email content extraction"""
    service, _ = mock_gmail_service
    
    message = {
        'id': 'test_id',
        'payload': {
            'headers': [
                {'name': 'Subject', 'value': 'Package Delivered'},
                {'name': 'From', 'value': 'ups@shipping.com'},
                {'name': 'Date', 'value': 'Wed, 10 Jan 2024 10:00:00 +0000'}
            ],
            'mimeType': 'text/plain',
            'body': {'data': 'VGVzdCBib2R5'}  # Base64 encoded "Test body"
        },
        'snippet': 'Your package has been delivered',
        'threadId': 'thread123'
    }
    
    content = service.extract_email_content(message)
    
    assert content['id'] == 'test_id'
    assert content['subject'] == 'Package Delivered'
    assert content['sender'] == 'ups@shipping.com'
    assert content['snippet'] == 'Your package has been delivered'
    assert content['thread_id'] == 'thread123'
    assert isinstance(content['date'], datetime)

def test_is_package_related_email(mock_gmail_service):
    """Test package-related email detection"""
    service, _ = mock_gmail_service
    
    # Package-related email
    package_email = {
        'subject': 'Your Amazon order has shipped',
        'body': 'Tracking number: 1Z999AA1234567890',
        'snippet': 'Your package is on the way'
    }
    assert service.is_package_related_email(package_email) is True
    
    # Non-package email
    regular_email = {
        'subject': 'Meeting reminder',
        'body': 'Don\'t forget about our meeting tomorrow',
        'snippet': 'Meeting at 2 PM'
    }
    assert service.is_package_related_email(regular_email) is False

def test_get_user_gmail_service(test_db, test_user):
    """Test getting Gmail service for user"""
    with patch('app.gmail_service.refresh_user_credentials') as mock_refresh:
        mock_credentials = MagicMock()
        mock_refresh.return_value = mock_credentials
        
        with patch('app.gmail_service.GmailService') as mock_gmail_service:
            service = get_user_gmail_service(test_user, test_db)
            mock_gmail_service.assert_called_once_with(mock_credentials)

def test_get_user_gmail_service_no_credentials(test_db, test_user):
    """Test getting Gmail service for user with no credentials"""
    with patch('app.gmail_service.refresh_user_credentials') as mock_refresh:
        mock_refresh.return_value = None
        
        service = get_user_gmail_service(test_user, test_db)
        assert service is None

def test_mark_email_processed(test_db, test_user):
    """Test marking email as processed"""
    mark_email_processed(
        test_user.id, 
        "email123", 
        True, 
        None, 
        100, 
        test_db
    )
    
    log = test_db.query(EmailProcessingLog).filter(
        EmailProcessingLog.user_id == test_user.id,
        EmailProcessingLog.email_id == "email123"
    ).first()
    
    assert log is not None
    assert log.success is True
    assert log.processing_time_ms == 100

def test_is_email_already_processed(test_db, test_user):
    """Test checking if email is already processed"""
    # Email not processed yet
    assert is_email_already_processed(test_user.id, "email123", test_db) is False
    
    # Mark email as processed
    mark_email_processed(test_user.id, "email123", True, None, None, test_db)
    
    # Email should now be marked as processed
    assert is_email_already_processed(test_user.id, "email123", test_db) is True