import time
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import User, Package
from app.gmail_service import (
    get_user_gmail_service, 
    mark_email_processed, 
    is_email_already_processed
)
from app.ai_parser import parse_package_info, enhance_package_name
from app.config import settings

class EmailProcessor:
    def __init__(self):
        self.db = SessionLocal()
    
    def process_user_emails(self, user: User, force_initial_scan: bool = False) -> dict:
        """Process emails for a single user"""
        start_time = time.time()
        results = {
            'user_id': user.id,
            'user_email': user.email,
            'emails_processed': 0,
            'packages_found': 0,
            'errors': [],
            'processing_time': 0
        }
        
        try:
            # Get Gmail service for user
            gmail_service = get_user_gmail_service(user, self.db)
            if not gmail_service:
                results['errors'].append("Unable to access Gmail - credentials may be expired")
                return results
            
            # Determine date range for email processing
            if force_initial_scan or not user.last_email_check:
                # Initial scan - get last N days
                since_date = datetime.utcnow() - timedelta(days=settings.initial_days_to_scan)
            else:
                # Incremental scan - get emails since last check
                since_date = user.last_email_check
            
            # Get new messages
            messages = gmail_service.get_new_messages(since_date)
            results['emails_processed'] = len(messages)
            
            for message in messages:
                try:
                    # Skip if already processed
                    if is_email_already_processed(user.id, message['id'], self.db):
                        continue
                    
                    # Extract email content
                    email_content = gmail_service.extract_email_content(message)
                    
                    # Quick heuristic check
                    if not gmail_service.is_package_related_email(email_content):
                        # Mark as processed but no package found
                        mark_email_processed(
                            user.id, message['id'], True, 
                            "Not package-related", None, self.db
                        )
                        continue
                    
                    # Use AI to parse package information
                    package_data, confidence = parse_package_info(email_content)
                    
                    if package_data and confidence > 30:  # Minimum confidence threshold
                        # Enhance package name
                        enhanced_name = enhance_package_name(package_data, email_content)
                        
                        # Create package record
                        package = Package(
                            user_id=user.id,
                            tracking_number=package_data.get('tracking_number'),
                            carrier=package_data.get('carrier'),
                            package_name=enhanced_name,
                            description=package_data.get('description'),
                            status=package_data.get('status', 'pending'),
                            source_email_id=message['id'],
                            source_subject=email_content['subject'],
                            source_sender=email_content['sender'],
                            source_date=email_content['date'],
                            ai_confidence=confidence,
                            raw_email_content=email_content['body'],
                            parsed_data=package_data
                        )
                        
                        # Parse estimated delivery date
                        if package_data.get('estimated_delivery'):
                            try:
                                package.estimated_delivery = datetime.fromisoformat(
                                    package_data['estimated_delivery'].replace('Z', '+00:00')
                                )
                            except:
                                pass  # Ignore date parsing errors
                        
                        self.db.add(package)
                        results['packages_found'] += 1
                        
                        # Mark as processed successfully
                        mark_email_processed(
                            user.id, message['id'], True, None, None, self.db
                        )
                    else:
                        # Mark as processed but no package found
                        mark_email_processed(
                            user.id, message['id'], True, 
                            f"Low confidence: {confidence}%", None, self.db
                        )
                
                except Exception as e:
                    error_msg = f"Error processing email {message.get('id', 'unknown')}: {str(e)}"
                    results['errors'].append(error_msg)
                    
                    # Mark as processed with error
                    mark_email_processed(
                        user.id, message.get('id', ''), False, error_msg, None, self.db
                    )
            
            # Update user's last check time
            user.last_email_check = datetime.utcnow()
            self.db.commit()
            
        except Exception as e:
            error_msg = f"Error processing emails for user {user.email}: {str(e)}"
            results['errors'].append(error_msg)
            self.db.rollback()
        
        results['processing_time'] = round((time.time() - start_time) * 1000)  # ms
        return results
    
    def process_all_users(self) -> List[dict]:
        """Process emails for all active users"""
        results = []
        
        try:
            users = self.db.query(User).filter(User.is_active == True).all()
            
            for user in users:
                try:
                    user_result = self.process_user_emails(user)
                    results.append(user_result)
                except Exception as e:
                    results.append({
                        'user_id': user.id,
                        'user_email': user.email,
                        'emails_processed': 0,
                        'packages_found': 0,
                        'errors': [f"Failed to process user: {str(e)}"],
                        'processing_time': 0
                    })
        
        except Exception as e:
            print(f"Error in process_all_users: {e}")
        
        finally:
            self.db.close()
        
        return results
    
    def process_user_initial_scan(self, user: User) -> dict:
        """Force initial scan for a user (e.g., after first login)"""
        return self.process_user_emails(user, force_initial_scan=True)

def process_single_user(user_id: int) -> dict:
    """Standalone function to process a single user's emails"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {'error': 'User not found'}
        
        processor = EmailProcessor()
        processor.db = db
        return processor.process_user_emails(user)
    finally:
        db.close()

def process_all_users_background() -> List[dict]:
    """Background task to process all users"""
    processor = EmailProcessor()
    return processor.process_all_users()