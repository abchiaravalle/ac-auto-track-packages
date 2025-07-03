import json
import re
from typing import Dict, Any, Optional, Tuple
from openai import OpenAI
from app.config import settings

client = OpenAI(api_key=settings.openai_api_key)

def parse_package_info(email_content: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], int]:
    """
    Parse package information from email content using OpenAI.
    Returns (parsed_data, confidence_score)
    """
    
    # Combine email content for analysis
    text_content = f"""
    Subject: {email_content['subject']}
    From: {email_content['sender']}
    Date: {email_content['date']}
    
    Email Content:
    {email_content['body']}
    
    Snippet: {email_content['snippet']}
    """
    
    system_prompt = """
    You are an expert at extracting package tracking information from emails. 
    Analyze the provided email and extract any package/shipment information.
    
    Return a JSON object with the following structure:
    {
        "is_package_email": boolean,
        "confidence": integer (0-100),
        "package_name": string (descriptive name for the package based on context),
        "tracking_number": string or null,
        "carrier": string or null (e.g., "UPS", "FedEx", "USPS", "DHL", "Amazon"),
        "status": string or null (e.g., "shipped", "in_transit", "delivered", "pending"),
        "estimated_delivery": string or null (ISO date format if found),
        "description": string or null (any additional details about the package),
        "reasoning": string (brief explanation of how you determined this information)
    }
    
    Guidelines:
    - Only set is_package_email to true if this is clearly about a package/shipment
    - Be creative with package_name - use context clues from the email content, sender, or subject
    - Look for tracking numbers (usually alphanumeric codes)
    - Identify carriers from sender domain or mentions in content
    - Set confidence based on how certain you are about the extracted information
    - If no package information is found, set is_package_email to false
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text_content}
            ],
            temperature=0.1,
            max_tokens=1000
        )
        
        content = response.choices[0].message.content.strip()
        
        # Try to extract JSON from the response
        try:
            # Look for JSON in the response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                parsed_data = json.loads(json_match.group())
            else:
                parsed_data = json.loads(content)
            
            # Validate the structure
            if not isinstance(parsed_data, dict) or 'is_package_email' not in parsed_data:
                return None, 0
            
            confidence = parsed_data.get('confidence', 0)
            
            # Only return data if it's identified as a package email
            if parsed_data.get('is_package_email', False):
                return parsed_data, confidence
            else:
                return None, 0
                
        except json.JSONDecodeError:
            print(f"Failed to parse JSON from OpenAI response: {content}")
            return None, 0
            
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None, 0

def enhance_package_name(package_data: Dict[str, Any], email_content: Dict[str, Any]) -> str:
    """
    Enhance package name using additional context clues
    """
    name = package_data.get('package_name', '')
    
    if not name or name.lower() in ['package', 'shipment', 'order', 'delivery']:
        # Try to extract a better name from context
        sender = email_content.get('sender', '').lower()
        subject = email_content.get('subject', '').lower()
        
        # Common retailers and their patterns
        if 'amazon' in sender:
            name = 'Amazon Order'
        elif 'ebay' in sender:
            name = 'eBay Purchase'
        elif 'etsy' in sender:
            name = 'Etsy Order'
        elif 'ups' in sender:
            name = 'UPS Package'
        elif 'fedex' in sender:
            name = 'FedEx Package'
        elif 'usps' in sender or 'postal' in sender:
            name = 'USPS Package'
        elif any(word in subject for word in ['order', 'purchase', 'buy']):
            # Extract potential product names from subject
            subject_words = subject.split()
            if 'order' in subject_words:
                idx = subject_words.index('order')
                if idx > 0:
                    name = ' '.join(subject_words[:idx]).title()
        
        # Fallback to generic name with sender
        if not name or len(name) < 3:
            sender_name = sender.split('@')[0] if '@' in sender else sender
            name = f"Package from {sender_name.title()}"
    
    return name

def extract_tracking_urls(email_content: Dict[str, Any]) -> list:
    """Extract tracking URLs from email content"""
    text = email_content.get('body', '') + ' ' + email_content.get('snippet', '')
    
    # Common tracking URL patterns
    tracking_patterns = [
        r'https?://[^\s]*track[^\s]*',
        r'https?://[^\s]*shipping[^\s]*',
        r'https?://[^\s]*ups\.com[^\s]*',
        r'https?://[^\s]*fedex\.com[^\s]*',
        r'https?://[^\s]*usps\.com[^\s]*',
        r'https?://[^\s]*amazon\.com[^\s]*track[^\s]*'
    ]
    
    urls = []
    for pattern in tracking_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        urls.extend(matches)
    
    return list(set(urls))  # Remove duplicates