import os
from typing import Optional
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./package_tracker.db"
    
    # Google OAuth
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str = "http://localhost:8000/auth/callback"
    
    # OpenAI
    openai_api_key: str
    
    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Admin
    admin_emails: str = ""  # Comma-separated list of admin emails
    
    # Gmail API
    gmail_scopes: list = ["https://www.googleapis.com/auth/gmail.readonly"]
    
    # Email processing
    initial_days_to_scan: int = 7
    check_interval_minutes: int = 30
    
    class Config:
        env_file = ".env"
        
    @property
    def admin_email_list(self) -> list[str]:
        return [email.strip() for email in self.admin_emails.split(",") if email.strip()]

settings = Settings()