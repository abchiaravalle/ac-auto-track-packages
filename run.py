#!/usr/bin/env python3
"""
Gmail Package Tracker - Run Script

This script provides a convenient way to run the application with proper
error handling and environment validation.
"""

import os
import sys
import subprocess
from pathlib import Path

def check_env_file():
    """Check if .env file exists and has required variables"""
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ Error: .env file not found!")
        print("📝 Please copy .env.example to .env and configure your credentials:")
        print("   cp .env.example .env")
        return False
    
    # Check for required variables
    required_vars = [
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET", 
        "OPENAI_API_KEY",
        "SECRET_KEY"
    ]
    
    with open(env_file) as f:
        content = f.read()
    
    missing_vars = []
    for var in required_vars:
        if f"{var}=your_" in content or f"{var}=" not in content:
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Error: Missing or unconfigured environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n📝 Please configure these variables in your .env file")
        return False
    
    return True

def check_dependencies():
    """Check if required packages are installed"""
    try:
        import fastapi
        import uvicorn
        import sqlalchemy
        import openai
        import google.auth
        print("✅ All dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Error: Missing dependency - {e}")
        print("📦 Please install dependencies:")
        print("   pip install -r requirements.txt")
        return False

def create_directories():
    """Create necessary directories"""
    directories = [
        "app/static",
        "app/templates", 
        "data"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("📁 Created necessary directories")

def run_application():
    """Run the FastAPI application"""
    print("🚀 Starting Gmail Package Tracker...")
    print("📧 Web Interface: http://localhost:8000")
    print("🏥 Health Check: http://localhost:8000/health")
    print("👑 Admin Panel: http://localhost:8000/admin")
    print("\n📝 Press Ctrl+C to stop the server\n")
    
    try:
        # Run with uvicorn
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

def main():
    """Main function"""
    print("📦 Gmail Package Tracker - Setup and Run")
    print("=" * 50)
    
    # Check environment file
    if not check_env_file():
        sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Run application
    run_application()

if __name__ == "__main__":
    main()