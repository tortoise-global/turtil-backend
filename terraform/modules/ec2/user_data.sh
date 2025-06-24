#!/bin/bash
# ============================================================================
# USER DATA SCRIPT FOR TURTIL BACKEND INSTANCES
# ============================================================================
# This script sets up the application environment and starts the Docker container

set -e

# Update system
apt-get update -y
apt-get install -y docker.io awscli jq

# Start Docker service
systemctl start docker
systemctl enable docker

# Add ubuntu user to docker group
usermod -aG docker ubuntu

# Create application directory
mkdir -p /opt/turtil-backend
cd /opt/turtil-backend

# Environment variables for the application
cat > .env << 'EOF'
# Application Configuration
PROJECT_NAME=${project_name}
ENVIRONMENT=${environment}
VERSION=${app_version}
DEBUG=${app_debug}
LOG_LEVEL=${app_log_level}

# Database Configuration
DATABASE_URL=${app_database_url}

# Security Configuration
SECRET_KEY=${app_secret_key}
ALGORITHM=${app_algorithm}
ACCESS_TOKEN_EXPIRE_MINUTES=${app_access_token_expire_minutes}

# Rate Limiting
RATE_LIMIT_CALLS=${app_rate_limit_calls}
RATE_LIMIT_PERIOD=${app_rate_limit_period}

# OTP Configuration
OTP_EXPIRY_MINUTES=${app_otp_expiry_minutes}

# AWS Configuration
AWS_ACCESS_KEY_ID=${app_aws_access_key_id}
AWS_SECRET_ACCESS_KEY=${app_aws_secret_access_key}
AWS_REGION=${aws_region}
AWS_SES_FROM_EMAIL=${app_aws_ses_from_email}
AWS_SES_REGION=${app_aws_ses_region}

# Redis Configuration (Upstash)
UPSTASH_REDIS_URL=${app_upstash_redis_url}
UPSTASH_REDIS_TOKEN=${app_upstash_redis_token}
REDIS_USER_CACHE_TTL=${app_redis_user_cache_ttl}
REDIS_BLACKLIST_TTL=${app_redis_blacklist_ttl}
EOF

# Set proper permissions
chmod 600 .env
chown ubuntu:ubuntu .env

# Create systemd service for the application
cat > /etc/systemd/system/turtil-backend.service << 'EOF'
[Unit]
Description=Turtil Backend Application
After=docker.service
Requires=docker.service

[Service]
Type=forking
RemainAfterExit=yes
WorkingDirectory=/opt/turtil-backend
ExecStart=/opt/turtil-backend/start.sh
ExecStop=/opt/turtil-backend/stop.sh
User=ubuntu
Group=ubuntu

[Install]
WantedBy=multi-user.target
EOF

# Create start script
cat > start.sh << 'EOF'
#!/bin/bash
set -e

# Login to ECR
aws ecr get-login-password --region ${aws_region} | docker login --username AWS --password-stdin ${ecr_account_id}.dkr.ecr.${aws_region}.amazonaws.com

# Pull latest image
IMAGE_URI="${ecr_account_id}.dkr.ecr.${aws_region}.amazonaws.com/${project_name}-${environment}:latest"
docker pull $IMAGE_URI || echo "Failed to pull latest image, using cached version if available"

# Stop existing container if running
docker stop ${project_name}-${environment} 2>/dev/null || true
docker rm ${project_name}-${environment} 2>/dev/null || true

# Run the container
docker run -d \
  --name ${project_name}-${environment} \
  --restart unless-stopped \
  -p 8000:8000 \
  -p 80:8000 \
  --env-file /opt/turtil-backend/.env \
  --log-driver=awslogs \
  --log-opt awslogs-group=/aws/ec2/${project_name}-${environment} \
  --log-opt awslogs-region=${aws_region} \
  --log-opt awslogs-create-group=true \
  $IMAGE_URI

echo "Application started successfully"
EOF

# Create stop script
cat > stop.sh << 'EOF'
#!/bin/bash
docker stop ${project_name}-${environment} 2>/dev/null || true
docker rm ${project_name}-${environment} 2>/dev/null || true
echo "Application stopped"
EOF

# Make scripts executable
chmod +x start.sh stop.sh
chown ubuntu:ubuntu start.sh stop.sh

# Create health check script
cat > health-check.sh << 'EOF'
#!/bin/bash
# Health check script for the application

MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "$(date): Health check passed"
        exit 0
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "$(date): Health check failed (attempt $RETRY_COUNT/$MAX_RETRIES)"
    sleep 10
done

echo "$(date): Health check failed after $MAX_RETRIES attempts"
exit 1
EOF

chmod +x health-check.sh
chown ubuntu:ubuntu health-check.sh

# Create log rotation configuration
cat > /etc/logrotate.d/turtil-backend << 'EOF'
/var/log/turtil-backend/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
EOF

# Create log directory
mkdir -p /var/log/turtil-backend
chown ubuntu:ubuntu /var/log/turtil-backend

# Enable and start the service
systemctl daemon-reload
systemctl enable turtil-backend
systemctl start turtil-backend

# Install CloudWatch agent for monitoring
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/arm64/latest/amazon-cloudwatch-agent.deb
dpkg -i amazon-cloudwatch-agent.deb

# Create CloudWatch agent configuration
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'
{
    "agent": {
        "metrics_collection_interval": 60,
        "run_as_user": "cwagent"
    },
    "metrics": {
        "namespace": "TurtilBackend/${environment}",
        "metrics_collected": {
            "cpu": {
                "measurement": [
                    "cpu_usage_idle",
                    "cpu_usage_iowait",
                    "cpu_usage_user",
                    "cpu_usage_system"
                ],
                "metrics_collection_interval": 60
            },
            "disk": {
                "measurement": [
                    "used_percent"
                ],
                "metrics_collection_interval": 60,
                "resources": [
                    "*"
                ]
            },
            "mem": {
                "measurement": [
                    "mem_used_percent"
                ],
                "metrics_collection_interval": 60
            }
        }
    },
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "/var/log/turtil-backend/*.log",
                        "log_group_name": "/aws/ec2/${project_name}-${environment}",
                        "log_stream_name": "{instance_id}/application.log"
                    }
                ]
            }
        }
    }
}
EOF

# Start CloudWatch agent
systemctl enable amazon-cloudwatch-agent
systemctl start amazon-cloudwatch-agent

# Log completion
echo "$(date): User data script completed successfully" >> /var/log/turtil-backend/startup.log

# Run initial health check in background
nohup bash -c "sleep 60 && /opt/turtil-backend/health-check.sh" >> /var/log/turtil-backend/startup.log 2>&1 &