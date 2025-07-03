import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from app.email_processor import EmailProcessor, process_single_user, process_all_users_background
from app.models import Package

@pytest.fixture
def email_processor(test_db):
    """Create an email processor with test database"""
    processor = EmailProcessor()
    processor.db = test_db
    return processor

def test_process_user_emails_no_gmail_service(email_processor, test_user):
    """Test processing emails when Gmail service is unavailable"""
    with patch('app.email_processor.get_user_gmail_service') as mock_get_service:
        mock_get_service.return_value = None
        
        result = email_processor.process_user_emails(test_user)
        
        assert result['user_id'] == test_user.id
        assert result['emails_processed'] == 0
        assert result['packages_found'] == 0
        assert len(result['errors']) == 1
        assert "Unable to access Gmail" in result['errors'][0]

def test_process_user_emails_initial_scan(email_processor, test_user):
    """Test initial email scan for new user"""
    mock_gmail_service = MagicMock()
    mock_messages = [
        {'id': 'msg1'},
        {'id': 'msg2'}
    ]
    mock_gmail_service.get_new_messages.return_value = mock_messages
    
    # Mock email content extraction
    mock_email_content = {
        'id': 'msg1',
        'subject': 'Amazon shipment',
        'sender': 'amazon@shipment.com',
        'date': datetime.utcnow(),
        'body': 'Your order has shipped',
        'snippet': 'Tracking info'
    }
    mock_gmail_service.extract_email_content.return_value = mock_email_content
    mock_gmail_service.is_package_related_email.return_value = True
    
    with patch('app.email_processor.get_user_gmail_service') as mock_get_service:
        mock_get_service.return_value = mock_gmail_service
        
        with patch('app.email_processor.is_email_already_processed') as mock_is_processed:
            mock_is_processed.return_value = False
            
            with patch('app.email_processor.parse_package_info') as mock_parse:
                mock_package_data = {
                    'package_name': 'Amazon Order',
                    'tracking_number': '123456',
                    'carrier': 'UPS',
                    'status': 'shipped'
                }
                mock_parse.return_value = (mock_package_data, 85)
                
                with patch('app.email_processor.enhance_package_name') as mock_enhance:
                    mock_enhance.return_value = 'Enhanced Amazon Order'
                    
                    result = email_processor.process_user_emails(test_user, force_initial_scan=True)
                    
                    assert result['emails_processed'] == 2
                    assert result['packages_found'] == 2  # One for each message

def test_process_user_emails_incremental_scan(email_processor, test_user):
    """Test incremental email scan for existing user"""
    # Set last email check time
    test_user.last_email_check = datetime.utcnow() - timedelta(hours=1)
    
    mock_gmail_service = MagicMock()
    mock_gmail_service.get_new_messages.return_value = []
    
    with patch('app.email_processor.get_user_gmail_service') as mock_get_service:
        mock_get_service.return_value = mock_gmail_service
        
        result = email_processor.process_user_emails(test_user)
        
        # Should call get_new_messages with last_email_check time
        mock_gmail_service.get_new_messages.assert_called_once_with(test_user.last_email_check)

def test_process_user_emails_skip_already_processed(email_processor, test_user):
    """Test skipping already processed emails"""
    mock_gmail_service = MagicMock()
    mock_messages = [{'id': 'msg1'}]
    mock_gmail_service.get_new_messages.return_value = mock_messages
    
    with patch('app.email_processor.get_user_gmail_service') as mock_get_service:
        mock_get_service.return_value = mock_gmail_service
        
        with patch('app.email_processor.is_email_already_processed') as mock_is_processed:
            mock_is_processed.return_value = True  # Email already processed
            
            result = email_processor.process_user_emails(test_user)
            
            assert result['emails_processed'] == 1
            assert result['packages_found'] == 0

def test_process_user_emails_non_package_email(email_processor, test_user):
    """Test processing non-package-related email"""
    mock_gmail_service = MagicMock()
    mock_messages = [{'id': 'msg1'}]
    mock_gmail_service.get_new_messages.return_value = mock_messages
    
    mock_email_content = {
        'id': 'msg1',
        'subject': 'Meeting reminder',
        'sender': 'colleague@company.com',
        'date': datetime.utcnow(),
        'body': 'Meeting tomorrow at 2 PM',
        'snippet': 'Meeting reminder'
    }
    mock_gmail_service.extract_email_content.return_value = mock_email_content
    mock_gmail_service.is_package_related_email.return_value = False  # Not package-related
    
    with patch('app.email_processor.get_user_gmail_service') as mock_get_service:
        mock_get_service.return_value = mock_gmail_service
        
        with patch('app.email_processor.is_email_already_processed') as mock_is_processed:
            mock_is_processed.return_value = False
            
            with patch('app.email_processor.mark_email_processed') as mock_mark:
                result = email_processor.process_user_emails(test_user)
                
                assert result['emails_processed'] == 1
                assert result['packages_found'] == 0
                # Should mark as processed with "Not package-related" message
                mock_mark.assert_called_once()

def test_process_user_emails_low_confidence(email_processor, test_user):
    """Test processing email with low AI confidence"""
    mock_gmail_service = MagicMock()
    mock_messages = [{'id': 'msg1'}]
    mock_gmail_service.get_new_messages.return_value = mock_messages
    
    mock_email_content = {
        'id': 'msg1',
        'subject': 'Maybe a package?',
        'sender': 'unknown@sender.com',
        'date': datetime.utcnow(),
        'body': 'Unclear content',
        'snippet': 'Unclear'
    }
    mock_gmail_service.extract_email_content.return_value = mock_email_content
    mock_gmail_service.is_package_related_email.return_value = True
    
    with patch('app.email_processor.get_user_gmail_service') as mock_get_service:
        mock_get_service.return_value = mock_gmail_service
        
        with patch('app.email_processor.is_email_already_processed') as mock_is_processed:
            mock_is_processed.return_value = False
            
            with patch('app.email_processor.parse_package_info') as mock_parse:
                mock_parse.return_value = (None, 20)  # Low confidence
                
                with patch('app.email_processor.mark_email_processed') as mock_mark:
                    result = email_processor.process_user_emails(test_user)
                    
                    assert result['emails_processed'] == 1
                    assert result['packages_found'] == 0
                    # Should mark as processed with low confidence message
                    mock_mark.assert_called_once()

def test_process_all_users(test_db, test_user, test_admin_user):
    """Test processing emails for all users"""
    with patch('app.email_processor.SessionLocal') as mock_session:
        mock_session.return_value = test_db
        
        with patch('app.email_processor.EmailProcessor.process_user_emails') as mock_process:
            mock_process.return_value = {
                'user_id': 1,
                'user_email': 'test@example.com',
                'emails_processed': 5,
                'packages_found': 2,
                'errors': [],
                'processing_time': 1000
            }
            
            processor = EmailProcessor()
            processor.db = test_db
            results = processor.process_all_users()
            
            assert len(results) == 2  # Two active users
            assert all('user_id' in result for result in results)

def test_process_single_user(test_db, test_user):
    """Test processing single user function"""
    with patch('app.email_processor.SessionLocal') as mock_session:
        mock_session.return_value = test_db
        
        with patch('app.email_processor.EmailProcessor.process_user_emails') as mock_process:
            mock_result = {
                'user_id': test_user.id,
                'emails_processed': 3,
                'packages_found': 1,
                'errors': []
            }
            mock_process.return_value = mock_result
            
            result = process_single_user(test_user.id)
            
            assert result['user_id'] == test_user.id
            assert result['emails_processed'] == 3

def test_process_single_user_not_found():
    """Test processing non-existent user"""
    with patch('app.email_processor.SessionLocal') as mock_session:
        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = None
        mock_session.return_value = mock_db
        
        result = process_single_user(999)
        
        assert 'error' in result
        assert result['error'] == 'User not found'

def test_process_all_users_background():
    """Test background processing function"""
    with patch('app.email_processor.EmailProcessor') as mock_processor_class:
        mock_processor = MagicMock()
        mock_processor.process_all_users.return_value = [{'test': 'result'}]
        mock_processor_class.return_value = mock_processor
        
        results = process_all_users_background()
        
        assert results == [{'test': 'result'}]
        mock_processor.process_all_users.assert_called_once()