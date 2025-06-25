#!/bin/bash

# ============================================================================
# EC2 USER DATA SCRIPT - DOCKER-READY AMI (Ubuntu 24.04 LTS)
# ============================================================================
# This script sets up the Turtil Backend application on Docker-ready AMI
# Docker, docker-compose, nginx, and AWS CLI are pre-installed in the AMI

set -e

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a /var/log/user-data.log
}

log "Starting user data script execution on Docker-ready AMI..."
log "AMI Info: $(cat /etc/ami-info 2>/dev/null || echo 'Custom Docker-ready AMI')"

# Verify Docker is running (should already be enabled in AMI)
log "Verifying Docker service..."
systemctl status docker || {
    log "Starting Docker service..."
    systemctl start docker
    systemctl enable docker
}

# Ensure ubuntu user is in docker group (should already be done in AMI)
usermod -a -G docker ubuntu || log "User already in docker group"

log "Docker setup verified - using pre-installed Docker from AMI"

# Configure nginx as reverse proxy
log "Configuring nginx reverse proxy..."
cat > /etc/nginx/nginx.conf << 'EOF'
user www-data;
worker_processes auto;
error_log /var/log/nginx/error.log;
pid /run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    server {
        listen 80;
        server_name dev.api.turtil.co;

        location / {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_connect_timeout 30s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
        }

        location /health {
            proxy_pass http://127.0.0.1:8000/health;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF

# Start and enable nginx
log "Starting and enabling nginx..."
systemctl start nginx
systemctl enable nginx
log "Nginx configuration completed"

# Verify AWS CLI (should be pre-installed in AMI)
log "Verifying AWS CLI installation..."
aws --version || {
    log "ERROR: AWS CLI not found in AMI"
    exit 1
}

# Get instance metadata
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
REGION="${aws_region}"

# Configure Docker to use ECR
log "Configuring ECR login..."
if ECR_PASSWORD=$(aws ecr get-login-password --region $REGION 2>&1); then
    echo "$ECR_PASSWORD" | docker login --username AWS --password-stdin ${ecr_repository_url}
    log "ECR login successful"
else
    log "ERROR: ECR login failed: $ECR_PASSWORD"
    exit 1
fi

# Pull and run the application
log "Pulling Docker image from ECR..."
if docker pull ${ecr_repository_url}:latest; then
    log "Docker image pull successful"
else
    log "ERROR: Failed to pull Docker image"
    exit 1
fi

# Create environment file for the container
log "Creating environment file..."
cat > /home/ubuntu/app.env << 'EOF'
ENVIRONMENT=${environment}
DEBUG=true
LOG_LEVEL=INFO
PORT=8000
EOF
chown ubuntu:ubuntu /home/ubuntu/app.env

# Create docker-compose.yml file with all environment variables
log "Creating docker-compose.yml file..."
cat > /home/ubuntu/docker-compose.yml << 'EOF'
version: '3.8'

services:
  turtil-backend:
    image: ${ecr_repository_url}:latest
    container_name: turtil-backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      # Project Configuration
      - PROJECT_NAME=turtil-backend
      - VERSION=1.0.0
      - ENVIRONMENT=${environment}
      - DEBUG=true
      - PORT=8000
      - LOG_LEVEL=INFO
      
      # Security & Authentication
      - SECRET_KEY=${app_secret_key}
      - ALGORITHM=${algorithm}
      - ACCESS_TOKEN_EXPIRE_MINUTES=${access_token_expire_minutes}
      - REFRESH_TOKEN_EXPIRE_MINUTES=${refresh_token_expire_minutes}
      
      # OTP Configuration
      - OTP_EXPIRY_MINUTES=${otp_expiry_minutes}
      - OTP_MAX_ATTEMPTS=${otp_max_attempts}
      - DEV_OTP=${dev_otp}
      
      # Application Settings
      - CORS_ORIGINS=${cors_origins}
      - ALLOWED_HOSTS=${allowed_hosts}
      - RATE_LIMIT_CALLS=${rate_limit_calls}
      - RATE_LIMIT_PERIOD=${rate_limit_period}
      
      # Database & Cache
      - DATABASE_URL=${database_url}
      - UPSTASH_REDIS_URL=${upstash_redis_url}
      - UPSTASH_REDIS_TOKEN=${upstash_redis_token}
      - REDIS_USER_CACHE_TTL=${redis_user_cache_ttl}
      - REDIS_BLACKLIST_TTL=${redis_blacklist_ttl}
      
      # AWS Services
      - AWS_ACCESS_KEY_ID=${aws_access_key_id}
      - AWS_SECRET_ACCESS_KEY=${aws_secret_access_key}
      - AWS_REGION=${aws_region}
      - AWS_SES_FROM_EMAIL=${aws_ses_from_email}
      - AWS_SES_REGION=${aws_region}
      - S3_BUCKET_NAME=${s3_bucket_name}
      
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
EOF
chown ubuntu:ubuntu /home/ubuntu/docker-compose.yml

# Run the container using docker-compose
log "Starting Docker container with docker-compose..."
cd /home/ubuntu
if docker-compose up -d; then
    log "Docker container started successfully with docker-compose"
else
    log "ERROR: Failed to start Docker container with docker-compose"
    exit 1
fi

# Set up log rotation for application logs
echo "Setting up log management..."
cat > /etc/logrotate.d/turtil-backend << 'EOF'
/var/log/turtil-backend/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 ubuntu ubuntu
}
EOF

# Create health check script
cat > /home/ubuntu/health-check.sh << 'EOF'
#!/bin/bash
# Check both nginx (port 80) and FastAPI (port 8000)
curl -f http://localhost/health && curl -f http://localhost:8000/health || exit 1
EOF
chmod +x /home/ubuntu/health-check.sh

# Final verification
log "Verifying deployment..."
sleep 10
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    log "✅ FastAPI health check passed"
else
    log "⚠️ FastAPI health check failed"
fi

if curl -f http://localhost/health > /dev/null 2>&1; then
    log "✅ Nginx health check passed"
else
    log "⚠️ Nginx health check failed"
fi

# Log deployment completion
log "Turtil Backend deployment completed"
log "Instance ID: $INSTANCE_ID"
log "Application URL: http://dev.api.turtil.co"
log "Direct URL: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8000"