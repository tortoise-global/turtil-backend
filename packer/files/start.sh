#!/bin/bash
set -e

# Change to application directory
cd /home/ec2-user

# Create logs directory if it doesn't exist
mkdir -p /var/log/turtil-backend

# Load environment variables from EC2 user data if available
if [ -f /home/ec2-user/.env/production.env ]; then
    echo "Loading environment variables from production.env"
    export $(cat /home/ec2-user/.env/production.env | grep -v '^#' | xargs)
else
    echo "Warning: production.env not found, using default values"
fi

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "Docker is not running. Starting Docker..."
    sudo systemctl start docker
    sleep 5
fi

# Skip pulling for local images
echo "Using locally built Docker images..."

# Stop existing containers
echo "Stopping existing containers..."
docker-compose -f docker-compose.yml down || true

# Start the application
echo "Starting Turtil Backend application..."
docker-compose -f docker-compose.yml up -d

# Check if containers are running
sleep 10
if docker-compose -f docker-compose.yml ps | grep -q "Up"; then
    echo "Turtil Backend application started successfully"
    
    # Wait for health check
    echo "Waiting for application health check..."
    for i in {1..30}; do
        if curl -f http://localhost:8000/health >/dev/null 2>&1; then
            echo "Application is healthy and ready to serve requests"
            exit 0
        fi
        echo "Waiting for application to be ready... ($i/30)"
        sleep 10
    done
    
    echo "Warning: Application health check timeout, but containers are running"
    exit 0
else
    echo "Error: Failed to start application containers"
    docker-compose -f docker-compose.yml logs
    exit 1
fi