"""
Student FastAPI Application
Separate application for Student Mobile App with single-device authentication
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi_pagination import add_pagination
import time
import logging

from app.config import settings

# Import Student API routers
from app.api.student import auth as student_auth
from app.api.student import registration as student_registration
from app.api.student import profile as student_profile

logger = logging.getLogger(__name__)

# Create Student FastAPI application
student_app = FastAPI(
    title="Turtil Student Mobile API",
    version=settings.version,
    description="Student Mobile App - Academic Registration and Profile Management API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


def setup_student_openapi():
    """Configure OpenAPI security scheme for Student authentication"""
    from fastapi.openapi.utils import get_openapi

    def custom_openapi():
        if student_app.openapi_schema:
            return student_app.openapi_schema

        openapi_schema = get_openapi(
            title=student_app.title,
            version=student_app.version,
            description=student_app.description,
            routes=student_app.routes,
        )

        # Add JWT Bearer security scheme for Student
        openapi_schema["components"]["securitySchemes"] = {
            "HTTPBearer": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT token for student authentication (single-device). Format: Bearer <token>",
            }
        }

        student_app.openapi_schema = openapi_schema
        return student_app.openapi_schema

    student_app.openapi = custom_openapi


# Setup OpenAPI customization
setup_student_openapi()

# Add CORS middleware (potentially different settings for mobile)
student_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# Add trusted host middleware
student_app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)


# Request timing middleware
@student_app.middleware("http")
async def add_process_time_header(request, call_next):
    """Add response time header"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-API-Type"] = "Student"
    return response


# Global exception handler
@student_app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Global exception handler for Student app"""
    logger.error(f"Student API - Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "statusCode": 500,
            "message": "Internal server error" if not settings.debug else str(exc),
            "success": False,
            "timestamp": time.time(),
            "api": "student"
        },
    )


# Health check endpoint
@student_app.get("/health", include_in_schema=False)
async def student_health_check():
    """Student specific health check"""
    try:
        from app.api.student.deps import check_student_system_health
        health_status = await check_student_system_health()
        return health_status
    except Exception as e:
        logger.error(f"Student health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy", 
                "error": str(e), 
                "timestamp": time.time(),
                "api": "student"
            },
        )


# App information endpoint
@student_app.get("/info", include_in_schema=False)
async def student_app_info():
    """Student application information"""
    return {
        "name": "Turtil Student Mobile API",
        "version": settings.version,
        "api_type": "student",
        "environment": settings.environment,
        "debug": settings.debug,
        "features": {
            "single_device_authentication": True,
            "academic_registration": True,
            "step_by_step_onboarding": True,
            "profile_management": True,
            "college_selection": True,
            "section_assignment": True,
            "mobile_optimized": True,
            "real_time_validation": True,
        },
        "authentication": "JWT with single-device enforcement",
        "documentation": "/docs",
        "registration_flow": [
            "signup",
            "verify-otp", 
            "setup-profile",
            "college-selection",
            "term-selection",
            "graduation-selection",
            "degree-selection",
            "branch-selection",
            "section-selection"
        ]
    }


# Include Student API routers
student_app.include_router(student_auth.router, prefix="/api/student")
student_app.include_router(student_registration.router, prefix="/api/student")
student_app.include_router(student_profile.router, prefix="/api/student")

# Add pagination
add_pagination(student_app)

logger.info("Student FastAPI application configured successfully")