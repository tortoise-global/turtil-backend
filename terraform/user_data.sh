#!/bin/bash

# ============================================================================
# EC2 USER DATA SCRIPT - DEV ENVIRONMENT
# ============================================================================
# This script sets up Docker and runs the Turtil Backend application

set -e

# Update system
yum update -y

# Install Docker and nginx
yum install -y docker nginx
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

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
systemctl start nginx
systemctl enable nginx

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install

# Get instance metadata
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
REGION="${aws_region}"

# Configure Docker to use ECR
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin ${ecr_repository_url}

# Pull and run the application
docker pull ${ecr_repository_url}:latest

# Create environment file for the container
cat > /home/ec2-user/app.env << 'EOF'
ENVIRONMENT=${environment}
DEBUG=true
LOG_LEVEL=INFO
PORT=8000
EOF

# Run the container
docker run -d \
  --name turtil-backend \
  --restart unless-stopped \
  -p 8000:8000 \
  --env-file /home/ec2-user/app.env \
  ${ecr_repository_url}:latest

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

# Log deployment completion
echo "$(date): Turtil Backend deployment completed" >> /var/log/user-data.log
echo "Instance ID: $INSTANCE_ID" >> /var/log/user-data.log
echo "Application URL: http://dev.api.turtil.co" >> /var/log/user-data.log