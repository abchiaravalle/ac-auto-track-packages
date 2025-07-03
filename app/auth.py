from datetime import datetime, timedelta
from typing import Optional
import json
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import User

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=[settings.algorithm])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        return email
    except JWTError:
        raise credentials_exception

def get_current_user(email: str = Depends(verify_token), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

def get_current_admin_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

def create_google_oauth_flow():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.google_redirect_uri]
            }
        },
        scopes=settings.gmail_scopes
    )
    flow.redirect_uri = settings.google_redirect_uri
    return flow

def get_user_info_from_google(credentials: Credentials):
    """Get user info from Google using the credentials"""
    service = build('oauth2', 'v2', credentials=credentials)
    user_info = service.userinfo().get().execute()
    return user_info

def encrypt_credentials(credentials: Credentials) -> str:
    """Convert credentials to JSON string for storage"""
    return credentials.to_json()

def decrypt_credentials(credentials_json: str) -> Credentials:
    """Convert JSON string back to credentials"""
    return Credentials.from_authorized_user_info(json.loads(credentials_json))

def refresh_user_credentials(user: User, db: Session) -> Optional[Credentials]:
    """Refresh user's Gmail credentials if needed"""
    if not user.gmail_credentials:
        return None
    
    try:
        credentials = decrypt_credentials(user.gmail_credentials)
        
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            user.gmail_credentials = encrypt_credentials(credentials)
            db.commit()
        
        return credentials
    except Exception as e:
        print(f"Error refreshing credentials for user {user.email}: {e}")
        return None