import pytest
from unittest.mock import patch, MagicMock
from app.ai_parser import parse_package_info, enhance_package_name, extract_tracking_urls

def test_parse_package_info_success(sample_email_content, mock_openai_response):
    """Test successful package parsing"""
    with patch('app.ai_parser.client') as mock_client:
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"is_package_email": true, "confidence": 85, "package_name": "Amazon Order", "tracking_number": "1Z999AA1234567890", "carrier": "UPS", "status": "shipped", "estimated_delivery": "2024-01-15T00:00:00Z", "description": "Electronics order", "reasoning": "Clear tracking info"}'
        mock_client.chat.completions.create.return_value = mock_response
        
        result, confidence = parse_package_info(sample_email_content)
        
        assert result is not None
        assert confidence == 85
        assert result["package_name"] == "Amazon Order"
        assert result["tracking_number"] == "1Z999AA1234567890"
        assert result["carrier"] == "UPS"

def test_parse_package_info_non_package_email(sample_email_content):
    """Test parsing non-package email"""
    with patch('app.ai_parser.client') as mock_client:
        # Mock OpenAI response for non-package email
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"is_package_email": false, "confidence": 10}'
        mock_client.chat.completions.create.return_value = mock_response
        
        result, confidence = parse_package_info(sample_email_content)
        
        assert result is None
        assert confidence == 0

def test_parse_package_info_low_confidence(sample_email_content):
    """Test parsing with low confidence"""
    with patch('app.ai_parser.client') as mock_client:
        # Mock OpenAI response with low confidence
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"is_package_email": true, "confidence": 20, "package_name": "Unknown Package"}'
        mock_client.chat.completions.create.return_value = mock_response
        
        result, confidence = parse_package_info(sample_email_content)
        
        assert result is not None
        assert confidence == 20

def test_parse_package_info_api_error(sample_email_content):
    """Test handling OpenAI API errors"""
    with patch('app.ai_parser.client') as mock_client:
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        result, confidence = parse_package_info(sample_email_content)
        
        assert result is None
        assert confidence == 0

def test_enhance_package_name_amazon():
    """Test package name enhancement for Amazon"""
    package_data = {"package_name": "Package"}
    email_content = {"sender": "shipment-tracking@amazon.com", "subject": "Your order has shipped"}
    
    name = enhance_package_name(package_data, email_content)
    assert name == "Amazon Order"

def test_enhance_package_name_ups():
    """Test package name enhancement for UPS"""
    package_data = {"package_name": "Shipment"}
    email_content = {"sender": "quantum@ups.com", "subject": "UPS tracking notification"}
    
    name = enhance_package_name(package_data, email_content)
    assert name == "UPS Package"

def test_enhance_package_name_from_subject():
    """Test package name enhancement from subject"""
    package_data = {"package_name": "Order"}
    email_content = {"sender": "store@example.com", "subject": "Electronics order confirmation"}
    
    name = enhance_package_name(package_data, email_content)
    assert name == "Electronics"

def test_enhance_package_name_fallback():
    """Test package name enhancement fallback"""
    package_data = {"package_name": "Package"}
    email_content = {"sender": "info@randomstore.com", "subject": "Notification"}
    
    name = enhance_package_name(package_data, email_content)
    assert name == "Package from Info"

def test_extract_tracking_urls():
    """Test tracking URL extraction"""
    email_content = {
        "body": "Track your package at https://www.ups.com/track?tracknum=123 or visit https://amazon.com/track/456",
        "snippet": "Also check https://fedex.com/tracking/789"
    }
    
    urls = extract_tracking_urls(email_content)
    
    assert len(urls) >= 2
    assert any("ups.com" in url for url in urls)
    assert any("amazon.com" in url for url in urls)

def test_extract_tracking_urls_no_urls():
    """Test tracking URL extraction with no URLs"""
    email_content = {
        "body": "Your package has been shipped but no tracking links provided",
        "snippet": "Thank you for your order"
    }
    
    urls = extract_tracking_urls(email_content)
    assert len(urls) == 0