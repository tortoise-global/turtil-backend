"""
CMS FastAPI Application
Separate application for CMS (College Management System) with existing staff functionality
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi_pagination import add_pagination
import time
import logging

from app.config import settings

# Import CMS API routers
from app.api import signup
from app.api import session
from app.api import registration
from app.api.cms import (
    departments as cms_departments,
    staff as cms_staff,
    files as cms_files,
    terms as cms_terms,
    graduations as cms_graduations,
    degrees as cms_degrees,
    branches as cms_branches,
    subjects as cms_subjects,
    sections as cms_sections,
    students as cms_students,
    notifications as cms_notifications,
)

# Import dev router conditionally
if settings.debug:
    from app.api import dev as dev_api

logger = logging.getLogger(__name__)

# Create CMS FastAPI application
cms_app = FastAPI(
    title="Turtil CMS API",
    version=settings.version,
    description="College Management System - Staff and Administrative API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


def setup_cms_openapi():
    """Configure OpenAPI security scheme for CMS authentication"""
    from fastapi.openapi.utils import get_openapi

    def custom_openapi():
        if cms_app.openapi_schema:
            return cms_app.openapi_schema

        openapi_schema = get_openapi(
            title=cms_app.title,
            version=cms_app.version,
            description=cms_app.description,
            routes=cms_app.routes,
        )

        # Add JWT Bearer security scheme for CMS
        openapi_schema["components"]["securitySchemes"] = {
            "HTTPBearer": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT token for CMS staff authentication. Format: Bearer <token>",
            }
        }

        cms_app.openapi_schema = openapi_schema
        return cms_app.openapi_schema

    cms_app.openapi = custom_openapi


# Setup OpenAPI customization
setup_cms_openapi()

# Add CORS middleware
cms_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# Add trusted host middleware
cms_app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)


# Request timing middleware
@cms_app.middleware("http")
async def add_process_time_header(request, call_next):
    """Add response time header"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-API-Type"] = "CMS"
    return response


# Global exception handler
@cms_app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Global exception handler for CMS app"""
    logger.error(f"CMS API - Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "statusCode": 500,
            "message": "Internal server error" if not settings.debug else str(exc),
            "success": False,
            "timestamp": time.time(),
            "api": "cms"
        },
    )


# Health check endpoint
@cms_app.get("/health", include_in_schema=False)
async def cms_health_check():
    """CMS specific health check"""
    try:
        from app.api.deps import check_system_health
        health_status = await check_system_health()
        health_status["api"] = "cms"
        return health_status
    except Exception as e:
        logger.error(f"CMS health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy", 
                "error": str(e), 
                "timestamp": time.time(),
                "api": "cms"
            },
        )


# App information endpoint
@cms_app.get("/info", include_in_schema=False)
async def cms_app_info():
    """CMS application information"""
    return {
        "name": "Turtil CMS API",
        "version": settings.version,
        "api_type": "cms",
        "environment": settings.environment,
        "debug": settings.debug,
        "features": {
            "staff_management": True,
            "multi_device_sessions": True,
            "role_based_access": True,
            "college_management": True,
            "academic_programs": True,
            "department_management": True,
            "file_upload": True,
            "aws_s3_integration": True,
            "redis_caching": True,
            "student_management": True,
            "student_approval_workflow": True,
            "push_notifications": True,
            "notification_history": True,
        },
        "authentication": "JWT with multi-device sessions",
        "documentation": "/docs"
    }


# Include CMS API routers
# Authentication and session management
cms_app.include_router(signup.router, prefix="/api")
cms_app.include_router(session.router, prefix="/api")

# CMS specific routers
cms_app.include_router(registration.router, prefix="/api/cms")
cms_app.include_router(cms_departments.router, prefix="/api")
cms_app.include_router(cms_staff.router, prefix="/api")
cms_app.include_router(cms_files.router, prefix="/api")

# Academic program management routers
cms_app.include_router(cms_terms.router, prefix="/api")
cms_app.include_router(cms_graduations.router, prefix="/api")
cms_app.include_router(cms_degrees.router, prefix="/api")
cms_app.include_router(cms_branches.router, prefix="/api")
cms_app.include_router(cms_subjects.router, prefix="/api")
cms_app.include_router(cms_sections.router, prefix="/api")

# Student management router
cms_app.include_router(cms_students.router, prefix="/api")

# Notification management router
cms_app.include_router(cms_notifications.router, prefix="/api")

# Include dev router conditionally
if settings.debug:
    cms_app.include_router(dev_api.router, prefix="/api")

# Add pagination
add_pagination(cms_app)

logger.info("CMS FastAPI application configured successfully")