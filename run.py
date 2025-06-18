#!/usr/bin/env python3
"""
Turtil Backend Application Entry Point

This script starts the FastAPI application with the appropriate configuration
for the current environment.
"""

import uvicorn
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.config import settings


def main():
    """Main entry point for the application"""
    
    print(f"""
🚀 Starting {settings.project_name} v{settings.version}
📊 Environment: {settings.environment}
🔧 Debug mode: {settings.debug}
🌐 Server: http://0.0.0.0:8000
📚 API docs: {'http://0.0.0.0:8000/docs' if settings.debug else 'disabled'}
📡 Health check: http://0.0.0.0:8000/health
    """)
    
    # Configure uvicorn based on environment
    if settings.environment == "production":
        # Production configuration
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            workers=1,  # Use 1 worker for simplicity; scale with gunicorn if needed
            reload=False,
            log_level="info",
            access_log=False,
            server_header=False,
            date_header=False
        )
    else:
        # Development configuration
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level=settings.log_level.lower(),
            access_log=True,
            reload_dirs=[str(project_root / "app")]
        )


if __name__ == "__main__":
    main()