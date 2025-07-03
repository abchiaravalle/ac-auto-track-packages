from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    google_id = Column(String, unique=True, nullable=False)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Gmail API credentials (encrypted)
    gmail_credentials = Column(Text, nullable=True)
    last_email_check = Column(DateTime(timezone=True), nullable=True)
    
    packages = relationship("Package", back_populates="user")

class Package(Base):
    __tablename__ = "packages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Package information
    tracking_number = Column(String, nullable=True)
    carrier = Column(String, nullable=True)
    package_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Status tracking
    status = Column(String, default="pending")  # pending, shipped, delivered, etc.
    estimated_delivery = Column(DateTime(timezone=True), nullable=True)
    
    # Email source information
    source_email_id = Column(String, nullable=False)  # Gmail message ID
    source_subject = Column(String, nullable=True)
    source_sender = Column(String, nullable=True)
    source_date = Column(DateTime(timezone=True), nullable=False)
    
    # AI parsing results
    ai_confidence = Column(Integer, default=0)  # 0-100
    raw_email_content = Column(Text, nullable=True)
    parsed_data = Column(JSON, nullable=True)  # Store full AI response
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="packages")

class EmailProcessingLog(Base):
    __tablename__ = "email_processing_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    email_id = Column(String, nullable=False)  # Gmail message ID
    processed_at = Column(DateTime(timezone=True), server_default=func.now())
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    
    # To avoid reprocessing the same email
    __table_args__ = (
        {"sqlite_on_conflict": "IGNORE"},
    )