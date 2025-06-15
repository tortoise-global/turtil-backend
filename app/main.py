"""Main FastAPI application module.

This module initializes and configures the FastAPI application with:
- CORS middleware
- Security headers
- Rate limiting
- Request logging
- Global exception handling
- Database initialization
- API route registration
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.cms.routes import router as cms_router
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import setup_logging
from app.core.middleware import RateLimitMiddleware
from app.core.monitoring import (
    get_health_status,
    request_monitoring_middleware,
    setup_database_monitoring,
)
from app.core.redis_client import redis_client
from app.core.security_headers import SecurityHeadersMiddleware
from app.db.database import Base, engine
from app.models.cms import models


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.

    Handles startup and shutdown tasks for the FastAPI application.

    Args:
        app (FastAPI): The FastAPI application instance

    Yields:
        None: Yields control to the application
    """
    setup_logging()
    logger = logging.getLogger("startup")

    # Test PostgreSQL connection
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("✅ Successfully connected to PostgreSQL database")
    except Exception as e:
        logger.error(f"❌ Failed to connect to PostgreSQL database: {e}")

    # Create database tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/verified successfully")
    except Exception as e:
        logger.error(f"❌ Failed to create database tables: {e}")

    # Test Redis connection
    if redis_client.is_available():
        logger.info("✅ Successfully connected to Redis")
    else:
        logger.warning("⚠️ Redis connection not available - operating without cache")

    # Setup database monitoring
    setup_database_monitoring()
    logger.info("✅ Database monitoring enabled")

    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-ready FastAPI backend for college management system",
    version=settings.VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    calls=settings.RATE_LIMIT_CALLS,
    period=settings.RATE_LIMIT_PERIOD,
)

# Add monitoring middleware
app.middleware("http")(request_monitoring_middleware)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Middleware to add process time header to responses.

    Args:
        request (Request): The incoming request
        call_next: The next middleware or route handler

    Returns:
        Response: The response with X-Process-Time header added
    """
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Middleware to log request information.

    Args:
        request (Request): The incoming request
        call_next: The next middleware or route handler

    Returns:
        Response: The response from downstream handlers
    """
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time
    logger = logging.getLogger("api")
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.4f}s"
    )

    return response


# Register exception handlers
register_exception_handlers(app)


@app.get("/")
async def root():
    """Root endpoint that returns API information.

    Returns:
        dict: API name, version, environment, and status
    """
    return {
        "message": f"{settings.PROJECT_NAME} API",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "active",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint with detailed metrics.

    Returns:
        dict: Health status, timestamp, and system metrics
    """
    return get_health_status()


@app.get("/metrics")
async def get_metrics():
    """Get application metrics for monitoring.

    Returns:
        dict: Application performance metrics
    """
    from app.core.monitoring import PerformanceMonitor

    return PerformanceMonitor.get_metrics()


app.include_router(cms_router, prefix="/cms")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )
