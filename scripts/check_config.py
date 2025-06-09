#!/usr/bin/env python3
"""
Script to check if configuration is properly loaded from environment variables
"""

import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.config import settings

def check_config():
    print("🔧 Configuration Check")
    print("=" * 50)
    
    print(f"Project Name: {settings.PROJECT_NAME}")
    print(f"Version: {settings.VERSION}")
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Debug Mode: {settings.DEBUG}")
    print(f"Log Level: {settings.LOG_LEVEL}")
    print()
    
    print(f"Database URL: {settings.DATABASE_URL}")
    print(f"Secret Key: {settings.SECRET_KEY[:20]}...")
    print(f"Algorithm: {settings.ALGORITHM}")
    print(f"Token Expire Minutes: {settings.ACCESS_TOKEN_EXPIRE_MINUTES}")
    print()
    
    print(f"CORS Origins: {settings.CORS_ORIGINS}")
    print(f"Allowed Hosts: {settings.ALLOWED_HOSTS}")
    print()
    
    print(f"Rate Limit Calls: {settings.RATE_LIMIT_CALLS}")
    print(f"Rate Limit Period: {settings.RATE_LIMIT_PERIOD}")
    print()
    
    # Check if .env file exists
    env_file = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_file):
        print("✅ .env file found")
    else:
        print("❌ .env file not found")
    
    print("=" * 50)
    print("✅ Configuration loaded successfully!")

if __name__ == "__main__":
    check_config()