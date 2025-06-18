from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time
from typing import Dict, Any, Annotated

# Import configuration and core modules
from app.config import settings
from app.database import init_db, close_db
from app.redis_client import close_redis

# Import API routers
from app.api import auth, email, upload

# Import health check dependencies
from app.api.deps import check_system_health

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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


# Create FastAPI application
app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    description="Production-ready FastAPI backend with SQLAlchemy, Redis, and AWS integration",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# Add trusted host middleware for security
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts
)


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
            "timestamp": time.time()
        }
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
            "timestamp": time.time()
        }
    )


# Health check endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.project_name}",
        "version": settings.version,
        "environment": settings.environment,
        "status": "healthy",
        "timestamp": time.time()
    }


@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint"""
    try:
        health_status = await check_system_health()
        return health_status
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
        )


@app.get("/health/simple")
async def simple_health_check():
    """Simple health check for load balancers"""
    return {"status": "healthy"}


@app.get("/info")
async def app_info():
    """Application information endpoint"""
    return {
        "name": settings.project_name,
        "version": settings.version,
        "environment": settings.environment,
        "debug": settings.debug,
        "features": {
            "authentication": True,
            "email_otp": True,
            "file_upload": True,
            "aws_integration": True,
            "redis_caching": True,
            "camelcase_api": True
        },
        "endpoints": {
            "auth": "/api/auth",
            "email": "/api/email", 
            "upload": "/api/cms-image-upload",
            "health": "/health",
            "docs": "/docs" if settings.debug else "disabled"
        }
    }


# Include API routers
app.include_router(auth.router, prefix="/api")
app.include_router(email.router, prefix="/api")
app.include_router(upload.router, prefix="/api")


# Rate limiting endpoint (for testing)
if settings.debug:
    @app.get("/debug/config")
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
    🚀 {settings.project_name} v{settings.version} is starting...
    📊 Environment: {settings.environment}
    🔧 Debug mode: {settings.debug}
    🌐 CORS origins: {settings.cors_origins}
    📡 Health check: /health
    📚 API docs: {'/docs' if settings.debug else 'disabled'}
    """)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=settings.debug
    )