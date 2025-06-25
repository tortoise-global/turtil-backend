#!/bin/bash

# User Data Script for turtil-backend ${environment} environment
# This script runs on instance startup to deploy the application

set -e

exec > /var/log/user-data.log 2>&1

echo "$(date): Starting user data script for ${environment} environment..."

# Wait for cloud-init to complete
cloud-init status --wait

# Create application directory
mkdir -p /opt/turtil-backend
cd /opt/turtil-backend

# Create application environment file
cat > .env << EOF
# Environment Configuration
ENVIRONMENT=${environment}
AWS_REGION=${aws_region}

# Database Configuration
DATABASE_URL=${database_url}

# S3 Configuration
S3_BUCKET_NAME=${s3_bucket_name}

# Application Secrets
SECRET_KEY=${secret_key}

# AWS Credentials
AWS_ACCESS_KEY_ID=${aws_access_key_id}
AWS_SECRET_ACCESS_KEY=${aws_secret_access_key}

# Redis Configuration
UPSTASH_REDIS_URL=${upstash_redis_url}
UPSTASH_REDIS_TOKEN=${upstash_redis_token}

# Email Configuration
AWS_SES_FROM_EMAIL=${aws_ses_from_email}
AWS_SES_REGION=ap-south-1

# Application Settings
DEBUG=false
LOG_LEVEL=INFO
RATE_LIMIT_CALLS=100
RATE_LIMIT_PERIOD=60
OTP_EXPIRY_MINUTES=5
EOF

# Set proper permissions
chown ubuntu:ubuntu .env
chmod 600 .env

# Authenticate with ECR
aws ecr get-login-password --region ${aws_region} | docker login --username AWS --password-stdin ${ecr_repository_url}

# Pull and run the application
echo "$(date): Pulling Docker image from ECR..."
docker pull ${ecr_repository_url}:${environment}

# Stop any existing container
docker stop turtil-backend || true
docker rm turtil-backend || true

# Run the application container
echo "$(date): Starting application container..."
docker run -d \
  --name turtil-backend \
  --restart unless-stopped \
  -p 8000:8000 \
  --env-file .env \
  --health-cmd="curl -f http://localhost:8000/health || exit 1" \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  ${ecr_repository_url}:${environment}

# Configure nginx proxy
cat > /etc/nginx/sites-available/turtil-backend << EOF
server {
    listen 80;
    server_name _;
    
    location /health {
        proxy_pass http://localhost:8000/health;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Increase timeout for long-running requests
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF

# Enable the site
ln -sf /etc/nginx/sites-available/turtil-backend /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test and reload nginx
nginx -t && systemctl reload nginx

# Wait for application to be healthy
echo "$(date): Waiting for application to be healthy..."
RETRIES=0
MAX_RETRIES=20

while [ $RETRIES -lt $MAX_RETRIES ]; do
    if curl -f --max-time 5 http://localhost/health >/dev/null 2>&1; then
        echo "$(date): Application is healthy"
        break
    fi
    
    echo "$(date): Health check failed, retry $((RETRIES + 1))/$MAX_RETRIES"
    sleep 10
    RETRIES=$((RETRIES + 1))
done

if [ $RETRIES -eq $MAX_RETRIES ]; then
    echo "$(date): Application failed to become healthy"
    echo "$(date): Container logs:"
    docker logs turtil-backend
    exit 1
fi

echo "$(date): User data script completed successfully!"