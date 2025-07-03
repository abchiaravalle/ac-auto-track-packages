from fastapi import FastAPI, Depends, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
import uvicorn
from contextlib import asynccontextmanager

from app.config import settings
from app.database import engine, get_db
from app.models import Base, User, Package
from app.auth import (
    create_access_token, get_current_user, get_current_admin_user,
    create_google_oauth_flow, get_user_info_from_google, encrypt_credentials
)
from app.email_processor import EmailProcessor, process_single_user
from app.scheduler import email_scheduler

# Create database tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    email_scheduler.start()
    yield
    # Shutdown
    email_scheduler.stop()

app = FastAPI(
    title="Gmail Package Tracker",
    description="Track packages from Gmail with AI-powered parsing",
    version="1.0.0",
    lifespan=lifespan
)

# Static files and templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Root redirect
@app.get("/")
async def root():
    return RedirectResponse(url="/dashboard")

# Authentication routes
@app.get("/auth/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/auth/google")
async def google_auth():
    flow = create_google_oauth_flow()
    auth_url, _ = flow.authorization_url(prompt='consent')
    return RedirectResponse(url=auth_url)

@app.get("/auth/callback")
async def auth_callback(code: str, db: Session = Depends(get_db)):
    try:
        flow = create_google_oauth_flow()
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        user_info = get_user_info_from_google(credentials)
        
        # Check if user exists
        user = db.query(User).filter(User.google_id == user_info['id']).first()
        
        if not user:
            # Create new user
            user = User(
                email=user_info['email'],
                name=user_info['name'],
                google_id=user_info['id'],
                is_admin=user_info['email'] in settings.admin_email_list,
                gmail_credentials=encrypt_credentials(credentials)
            )
            db.add(user)
        else:
            # Update existing user
            user.gmail_credentials = encrypt_credentials(credentials)
            user.last_login = datetime.utcnow()
            user.is_admin = user.email in settings.admin_email_list
        
        db.commit()
        
        # Create access token
        access_token = create_access_token(data={"sub": user.email})
        
        # Trigger initial email scan for new users
        if not user.last_email_check:
            # Schedule initial scan in background
            from threading import Thread
            Thread(target=lambda: process_single_user(user.id)).start()
        
        response = RedirectResponse(url="/dashboard")
        response.set_cookie(key="access_token", value=access_token, httponly=True)
        return response
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")

@app.post("/auth/logout")
async def logout():
    response = RedirectResponse(url="/auth/login")
    response.delete_cookie("access_token")
    return response

# Get current user from cookie
def get_current_user_from_cookie(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    from app.auth import verify_token
    from fastapi.security import HTTPAuthorizationCredentials
    
    # Create fake credentials object
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    email = verify_token(credentials)
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Dashboard
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user: User = Depends(get_current_user_from_cookie), db: Session = Depends(get_db)):
    packages = db.query(Package).filter(Package.user_id == user.id).order_by(Package.created_at.desc()).all()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "packages": packages,
        "package_count": len(packages)
    })

# API Routes
@app.get("/api/packages")
async def get_packages(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    packages = db.query(Package).filter(Package.user_id == user.id).order_by(Package.created_at.desc()).all()
    return packages

@app.post("/api/process-emails")
async def trigger_email_processing(user: User = Depends(get_current_user)):
    from threading import Thread
    Thread(target=lambda: process_single_user(user.id)).start()
    return {"message": "Email processing started"}

@app.delete("/api/packages/{package_id}")
async def delete_package(package_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    package = db.query(Package).filter(Package.id == package_id, Package.user_id == user.id).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    db.delete(package)
    db.commit()
    return {"message": "Package deleted"}

# Admin routes
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, admin: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    scheduler_status = email_scheduler.get_status()
    
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "admin": admin,
        "users": users,
        "scheduler_status": scheduler_status
    })

@app.get("/admin/api/users")
async def get_all_users(admin: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return users

@app.post("/admin/api/users/{user_id}/toggle-active")
async def toggle_user_active(user_id: int, admin: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = not user.is_active
    db.commit()
    return {"message": f"User {'activated' if user.is_active else 'deactivated'}"}

@app.post("/admin/api/process-all-emails")
async def trigger_all_email_processing(admin: User = Depends(get_current_admin_user)):
    email_scheduler.trigger_immediate_processing()
    return {"message": "Email processing triggered for all users"}

@app.get("/admin/api/scheduler-status")
async def get_scheduler_status(admin: User = Depends(get_current_admin_user)):
    return email_scheduler.get_status()

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)