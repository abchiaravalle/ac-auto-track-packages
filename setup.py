#!/usr/bin/env python3
"""
Gmail Package Tracker - Setup Script

This script helps set up the application for the first time.
"""

import os
import sys
import secrets
import subprocess
from pathlib import Path

def generate_secret_key():
    """Generate a secure secret key"""
    return secrets.token_urlsafe(32)

def setup_env_file():
    """Set up the .env file from template"""
    env_example = Path(".env.example")
    env_file = Path(".env")
    
    if env_file.exists():
        response = input("📄 .env file already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("📝 Using existing .env file")
            return
    
    if not env_example.exists():
        print("❌ Error: .env.example file not found!")
        return False
    
    # Read template
    with open(env_example) as f:
        content = f.read()
    
    # Generate secret key
    secret_key = generate_secret_key()
    content = content.replace("your-super-secret-key-here-use-openssl-rand-base64-32", secret_key)
    
    # Write to .env
    with open(env_file, 'w') as f:
        f.write(content)
    
    print("✅ Created .env file with generated secret key")
    print("📝 Please edit .env and add your Google OAuth and OpenAI credentials")
    return True

def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing Python dependencies...")
    
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], check=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Error installing dependencies")
        return False

def create_directories():
    """Create necessary directories"""
    directories = [
        "app/static",
        "app/templates",
        "data",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("📁 Created application directories")

def run_tests():
    """Run the test suite"""
    print("🧪 Running tests...")
    
    try:
        subprocess.run([
            sys.executable, "-m", "pytest", "-v"
        ], check=True)
        print("✅ All tests passed")
        return True
    except subprocess.CalledProcessError:
        print("❌ Some tests failed")
        return False
    except FileNotFoundError:
        print("⚠️  pytest not found, skipping tests")
        return True

def print_next_steps():
    """Print next steps for the user"""
    print("\n" + "=" * 60)
    print("🎉 Setup Complete!")
    print("=" * 60)
    
    print("\n📝 Next Steps:")
    print("1. Edit .env file with your credentials:")
    print("   - Google OAuth client ID and secret")
    print("   - OpenAI API key")
    print("   - Admin email addresses")
    
    print("\n2. Get Google OAuth credentials:")
    print("   - Go to https://console.cloud.google.com/")
    print("   - Create a new project or select existing")
    print("   - Enable Gmail API")
    print("   - Create OAuth 2.0 credentials")
    print("   - Add redirect URI: http://localhost:8000/auth/callback")
    
    print("\n3. Get OpenAI API key:")
    print("   - Go to https://platform.openai.com/")
    print("   - Create an account and get API key")
    
    print("\n4. Run the application:")
    print("   python run.py")
    
    print("\n5. Alternative - Docker:")
    print("   docker-compose up -d")
    
    print("\n🌐 Access Points:")
    print("   - Web Interface: http://localhost:8000")
    print("   - Admin Panel: http://localhost:8000/admin")
    print("   - Health Check: http://localhost:8000/health")

def main():
    """Main setup function"""
    print("📦 Gmail Package Tracker - Initial Setup")
    print("=" * 50)
    
    # Create directories
    create_directories()
    
    # Setup environment file
    if not setup_env_file():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("⚠️  Continuing with potential missing dependencies...")
    
    # Run tests (optional)
    run_tests()
    
    # Print next steps
    print_next_steps()

if __name__ == "__main__":
    main()