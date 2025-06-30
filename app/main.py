from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi_pagination import add_pagination
from contextlib import asynccontextmanager
import logging
import time

# Import configuration and core modules
from app.config import settings
from app.database import init_db, close_db
from app.redis_client import close_redis

# Import sub-applications
from app.cms_app import cms_app
from app.student_app import student_app

# Import health check dependencies
from app.api.deps import check_system_health

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events
    """
    # Startup
    logger.info("Starting Turtil Backend...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    try:
        # Check PostgreSQL connection
        logger.info("🔍 Checking PostgreSQL connection...")
        from app.database import check_db_health

        db_healthy = await check_db_health()
        if db_healthy:
            logger.info("✅ PostgreSQL connection successful")
        else:
            logger.error("❌ PostgreSQL connection failed")
            raise Exception("PostgreSQL connection verification failed")

        # Check Redis connection
        logger.info("🔍 Checking Redis connection...")
        from app.redis_client import redis_client

        redis_healthy = await redis_client.ping()
        if redis_healthy:
            logger.info("✅ Redis connection successful")
        else:
            logger.error("❌ Redis connection failed")
            raise Exception("Redis connection verification failed")

        # Initialize database
        await init_db()
        logger.info("Database initialized successfully")

        # Print configuration in debug mode
        if settings.debug:
            from app.config import print_config

            print_config()

        logger.info("🚀 Turtil Backend started successfully - All connections verified")

    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Turtil Backend...")

    try:
        await close_db()
        await close_redis()
        logger.info("Turtil Backend shut down successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create main FastAPI application (no docs - they're in sub-apps)
app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    description="Turtil Backend - Multi-API Platform (CMS + Student Mobile)",
    docs_url=None,  # Disabled - use /docs-cms or /docs-student
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)


# Mount sub-applications
app.mount("/api/cms", cms_app)
app.mount("/api/student", student_app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# Add trusted host middleware for security
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add response time header"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Global HTTP exception handler with camelCase response"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "statusCode": exc.status_code,
            "message": exc.detail,
            "success": False,
            "timestamp": time.time(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "statusCode": 500,
            "message": "Internal server error" if not settings.debug else str(exc),
            "success": False,
            "timestamp": time.time(),
        },
    )


# Documentation redirect endpoints
@app.get("/docs-cms")
async def cms_docs_redirect():
    """Redirect to CMS API documentation"""
    return RedirectResponse(url="/api/cms/docs")

@app.get("/docs-student")
async def student_docs_redirect():
    """Redirect to Student API documentation"""
    return RedirectResponse(url="/api/student/docs")

# Root endpoint (hidden from Swagger)
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with API discovery"""
    return {
        "message": f"Welcome to {settings.project_name}",
        "version": settings.version,
        "environment": settings.environment,
        "status": "healthy",
        "apis": {
            "cms": {
                "description": "College Management System API",
                "documentation": "/docs-cms",
                "health": "/cms/health"
            },
            "student": {
                "description": "Student Mobile App API", 
                "documentation": "/docs-student",
                "health": "/student/health"
            }
        },
        "timestamp": time.time(),
    }


@app.get("/health", include_in_schema=False)
async def health_check():
    """Simple health check for AWS load balancers"""
    return {"status": "healthy"}


@app.get("/health/detailed", include_in_schema=False)
async def detailed_health_check():
    """Comprehensive health check endpoint with system diagnostics"""
    try:
        health_status = await check_system_health()
        return health_status
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e), "timestamp": time.time()},
        )


@app.get("/info", include_in_schema=False)
async def app_info():
    """Application information endpoint"""
    return {
        "name": settings.project_name,
        "version": settings.version,
        "environment": settings.environment,
        "debug": settings.debug,
        "architecture": "Multi-API Platform",
        "apis": {
            "cms": {
                "name": "Turtil CMS API",
                "description": "College Management System",
                "mount_path": "/cms",
                "documentation": "/docs-cms",
                "health": "/cms/health",
                "info": "/cms/info",
                "features": [
                    "staff_management",
                    "multi_device_sessions", 
                    "role_based_access",
                    "college_management",
                    "academic_programs",
                    "department_management",
                    "file_upload"
                ]
            },
            "student": {
                "name": "Turtil Student Mobile API",
                "description": "Student Mobile App",
                "mount_path": "/student", 
                "documentation": "/docs-student",
                "health": "/student/health",
                "info": "/student/info",
                "features": [
                    "single_device_authentication",
                    "academic_registration",
                    "step_by_step_onboarding",
                    "profile_management",
                    "college_selection",
                    "mobile_optimized"
                ]
            }
        },
        "shared_features": {
            "aws_s3_integration": True,
            "redis_caching": True,
            "postgresql_database": True,
            "jwt_authentication": True,
            "camelcase_api": True,
            "email_notifications": True
        },
        "endpoints": {
            "root": "/",
            "health": "/health",
            "health_detailed": "/health/detailed",
            "cms_docs": "/docs-cms",
            "student_docs": "/docs-student",
            "info": "/info"
        }
    }


# Add pagination to the main app (sub-apps have their own)
add_pagination(app)


# Rate limiting endpoint (for testing)
if settings.debug:

    @app.get("/debug/config", include_in_schema=False)
    async def debug_config():
        """Debug endpoint to view configuration (only in debug mode)"""
        from app.config import print_config

        print_config()
        return {"message": "Configuration printed to console"}


# Startup message
@app.on_event("startup")
async def startup_message():
    """Log startup message"""
    logger.info(f"""
    🚀 {settings.project_name} v{settings.version} Multi-API Platform
    📊 Environment: {settings.environment}
    🔧 Debug mode: {settings.debug}
    🌐 CORS origins: {settings.cors_origins}
    
    📚 API Documentation:
    🏢 CMS API: /docs-cms
    📱 Student API: /docs-student
    
    📡 Health Checks:
    🔍 Main: /health, /health/detailed
    🏢 CMS: /cms/health
    📱 Student: /student/health
    """)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=settings.debug,
    )
