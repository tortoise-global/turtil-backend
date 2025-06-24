#!/bin/bash

# ============================================================================
# EC2 USER DATA SCRIPT - DEV ENVIRONMENT
# ============================================================================
# This script sets up Docker and runs the Turtil Backend application

set -e

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a /var/log/user-data.log
}

log "Starting user data script execution..."

# Update system
log "Updating system packages..."
apt update -y

# Install Docker and nginx
log "Installing Docker, nginx, and unzip..."
apt install -y docker.io nginx unzip
log "Starting and enabling Docker service..."
systemctl start docker
systemctl enable docker
usermod -a -G docker ubuntu
log "Docker installation completed"

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
cat > /home/ubuntu/app.env << 'EOF'
ENVIRONMENT=${environment}
DEBUG=true
LOG_LEVEL=INFO
PORT=8000
EOF
chown ubuntu:ubuntu /home/ubuntu/app.env

# Run the container
log "Starting Docker container..."
if docker run -d \
  --name turtil-backend \
  --restart unless-stopped \
  -p 8000:8000 \
  --env-file /home/ubuntu/app.env \
  ${ecr_repository_url}:latest; then
    log "Docker container started successfully"
else
    log "ERROR: Failed to start Docker container"
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