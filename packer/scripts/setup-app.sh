#!/bin/bash
set -e

echo "Setting up Turtil Backend application..."

# Create application directory
sudo mkdir -p /opt/turtil-backend
sudo chown ec2-user:ec2-user /opt/turtil-backend

# Copy application files
cp -r /tmp/turtil-backend/* /opt/turtil-backend/
cd /opt/turtil-backend

# Remove unnecessary files from production build
rm -rf .git
rm -rf venv
rm -rf __pycache__
rm -rf .pytest_cache
rm -rf *.log
rm -f .env*
rm -rf terraform-infrastructure

# Build Docker image
echo "Building Docker image..."
sudo docker build -t turtil-backend:latest .

# Verify image was built successfully
sudo docker images | grep turtil-backend

# Create logs directory
sudo mkdir -p /var/log/turtil-backend
sudo chown ec2-user:ec2-user /var/log/turtil-backend

# Create environment file directory (will be populated by user data script)
mkdir -p /home/ec2-user/.env

# Copy build environment for reference (optional)
if [ -f /tmp/build.env ]; then
    cp /tmp/build.env /home/ec2-user/.env/build.env
    chown ec2-user:ec2-user /home/ec2-user/.env/build.env
fi

echo "Application setup completed successfully!"