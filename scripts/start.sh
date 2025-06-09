#!/bin/bash

# Production startup script for Turtil Backend

set -e

echo "Starting Turtil Backend..."

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start the application
echo "Starting application server..."
if [ "$ENVIRONMENT" = "production" ]; then
    exec gunicorn app.main:app \
        --workers 4 \
        --worker-class uvicorn.workers.UvicornWorker \
        --bind 0.0.0.0:8000 \
        --access-logfile - \
        --error-logfile - \
        --log-level info
else
    exec uvicorn app.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --reload \
        --log-level info
fi