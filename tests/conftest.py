import pytest
import tempfile
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.database import Base, get_db
from app.main import app
from app.models import User, Package
from app.config import settings

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///./test.db"

@pytest.fixture(scope="function")
def test_db():
    """Create a test database for each test"""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Clean up
        if os.path.exists("./test.db"):
            os.remove("./test.db")

@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client with test database"""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

@pytest.fixture
def test_user(test_db):
    """Create a test user"""
    user = User(
        email="test@example.com",
        name="Test User",
        google_id="test_google_id",
        is_admin=False,
        is_active=True,
        gmail_credentials='{"test": "credentials"}'
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user

@pytest.fixture
def test_admin_user(test_db):
    """Create a test admin user"""
    user = User(
        email="admin@example.com",
        name="Admin User",
        google_id="admin_google_id",
        is_admin=True,
        is_active=True,
        gmail_credentials='{"test": "credentials"}'
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user

@pytest.fixture
def test_package(test_db, test_user):
    """Create a test package"""
    package = Package(
        user_id=test_user.id,
        tracking_number="TEST123456",
        carrier="UPS",
        package_name="Test Package",
        description="A test package",
        status="shipped",
        source_email_id="test_email_id",
        source_subject="Test Email",
        source_sender="test@sender.com",
        source_date=test_user.created_at,
        ai_confidence=85
    )
    test_db.add(package)
    test_db.commit()
    test_db.refresh(package)
    return package

@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response"""
    return {
        "is_package_email": True,
        "confidence": 85,
        "package_name": "Amazon Order",
        "tracking_number": "1Z999AA1234567890",
        "carrier": "UPS",
        "status": "shipped",
        "estimated_delivery": "2024-01-15T00:00:00Z",
        "description": "Electronics order from Amazon",
        "reasoning": "Email contains tracking number and shipping confirmation"
    }

@pytest.fixture
def sample_email_content():
    """Sample email content for testing"""
    return {
        "id": "test_email_id",
        "subject": "Your Amazon order has shipped",
        "sender": "shipment-tracking@amazon.com",
        "date": "2024-01-10T10:00:00Z",
        "body": "Your order has shipped with tracking number 1Z999AA1234567890",
        "snippet": "Your order has shipped",
        "thread_id": "test_thread_id"
    }