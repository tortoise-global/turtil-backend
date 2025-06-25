#!/bin/bash

# ============================================================================
# EC2 USER DATA SCRIPT - DEV ENVIRONMENT (Amazon Linux 2023)
# ============================================================================
# This script sets up the Turtil Backend application (Docker pre-installed)

set -e

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a /var/log/user-data.log
}

log "Starting user data script execution..."

# Update system and install required packages
log "Updating system packages..."
dnf update -y

# Install docker-compose and nginx
log "Installing docker-compose, nginx, and unzip..."
dnf install -y nginx unzip
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
log "Starting and enabling Docker service..."
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user
log "Docker setup completed"

# Configure nginx as reverse proxy
cat > /etc/nginx/nginx.conf << 'EOF'
user nginx;
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

# Install AWS CLI v2
log "Installing AWS CLI v2..."
curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install
log "AWS CLI installation completed"

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
cat > /home/ec2-user/app.env << 'EOF'
ENVIRONMENT=${environment}
DEBUG=true
LOG_LEVEL=INFO
PORT=8000
EOF
chown ec2-user:ec2-user /home/ec2-user/app.env

# Create docker-compose.yml file with all environment variables
log "Creating docker-compose.yml file..."
cat > /home/ec2-user/docker-compose.yml << 'EOF'
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
chown ec2-user:ec2-user /home/ec2-user/docker-compose.yml

# Run the container using docker-compose
log "Starting Docker container with docker-compose..."
cd /home/ec2-user
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
    create 644 ec2-user ec2-user
}
EOF

# Create health check script
cat > /home/ec2-user/health-check.sh << 'EOF'
#!/bin/bash
# Check both nginx (port 80) and FastAPI (port 8000)
curl -f http://localhost/health && curl -f http://localhost:8000/health || exit 1
EOF
chmod +x /home/ec2-user/health-check.sh

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