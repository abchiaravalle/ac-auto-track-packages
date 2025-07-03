import pytest
from datetime import datetime
from app.models import User, Package, EmailProcessingLog

def test_user_creation(test_db):
    """Test user model creation"""
    user = User(
        email="test@example.com",
        name="Test User",
        google_id="google123",
        is_admin=False,
        is_active=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    
    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.name == "Test User"
    assert user.google_id == "google123"
    assert user.is_admin is False
    assert user.is_active is True
    assert user.created_at is not None

def test_user_relationships(test_db, test_user):
    """Test user-package relationship"""
    package = Package(
        user_id=test_user.id,
        package_name="Test Package",
        source_email_id="email123",
        source_subject="Test Subject",
        source_sender="test@sender.com",
        source_date=datetime.utcnow(),
        ai_confidence=80
    )
    test_db.add(package)
    test_db.commit()
    
    assert len(test_user.packages) == 1
    assert test_user.packages[0].package_name == "Test Package"

def test_package_creation(test_db, test_user):
    """Test package model creation"""
    package = Package(
        user_id=test_user.id,
        tracking_number="UPS123456",
        carrier="UPS",
        package_name="Amazon Order",
        description="Electronics",
        status="shipped",
        source_email_id="email123",
        source_subject="Shipment Notification",
        source_sender="amazon@shipment.com",
        source_date=datetime.utcnow(),
        ai_confidence=90
    )
    test_db.add(package)
    test_db.commit()
    test_db.refresh(package)
    
    assert package.id is not None
    assert package.user_id == test_user.id
    assert package.tracking_number == "UPS123456"
    assert package.carrier == "UPS"
    assert package.package_name == "Amazon Order"
    assert package.status == "shipped"
    assert package.ai_confidence == 90

def test_email_processing_log(test_db, test_user):
    """Test email processing log model"""
    log = EmailProcessingLog(
        user_id=test_user.id,
        email_id="email123",
        success=True,
        processing_time_ms=150
    )
    test_db.add(log)
    test_db.commit()
    test_db.refresh(log)
    
    assert log.id is not None
    assert log.user_id == test_user.id
    assert log.email_id == "email123"
    assert log.success is True
    assert log.processing_time_ms == 150
    assert log.processed_at is not None