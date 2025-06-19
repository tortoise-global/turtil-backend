#!/bin/bash
# Install Docker from official repository
sudo apt-get update -y
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=arm64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io
sudo systemctl start docker
sudo usermod -aG docker ubuntu  # Ubuntu uses "ubuntu" user

newgrp docker

# Install aws-cli
sudo apt install -y awscli

# Install Amazon ECR Credential Helper
sudo apt-get install -y amazon-ecr-credential-helper
sudo mkdir -p /root/.docker
sudo mkdir -p /home/ubuntu/.docker
echo '{"credsStore": "ecr-login"}' | sudo tee /root/.docker/config.json
echo '{"credsStore": "ecr-login"}' | sudo tee /home/ubuntu/.docker/config.json

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Nginx
sudo apt-get install -y nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Configure Nginx as a reverse proxy
cat <<'EOF' | sudo tee /etc/nginx/sites-available/default
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    root /var/www/html;
    index index.html index.htm index.nginx-debian.html;
    server_name _;

    # Main application proxy
    location / {
        add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS, PUT, DELETE';
        add_header 'Access-Control-Allow-Headers' 'Authorization';
        add_header 'Access-Control-Allow-Origins' '*';
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # Health check endpoint for ALB
    location /health {
        add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS, PUT, DELETE';
        add_header 'Access-Control-Allow-Headers' 'Authorization';
        add_header 'Access-Control-Allow-Origins' '*';
        proxy_pass http://localhost:8000/health;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Health check specific optimizations
        proxy_connect_timeout 1s;
        proxy_send_timeout 1s;
        proxy_read_timeout 1s;
    }

    # Detailed health check endpoint
    location /health/detailed {
        add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS, PUT, DELETE';
        add_header 'Access-Control-Allow-Headers' 'Authorization';
        add_header 'Access-Control-Allow-Origins' '*';
        proxy_pass http://localhost:8000/health/detailed;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 5s;
        proxy_send_timeout 5s;
        proxy_read_timeout 5s;
    }
}
EOF

# Test Nginx configuration and reload
sudo nginx -t
sudo systemctl reload nginx

# Pull latest image from ECR (IAM role handles authentication)
ECR_URI="${ecr_account_id}.dkr.ecr.ap-south-1.amazonaws.com"

aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin $ECR_URI

docker pull $ECR_URI/${ecr_repository_name}:latest

# Generate docker-compose.yml with environment variables
cat <<EOF > /home/ubuntu/docker-compose.yml
services:
  web:
    image: $ECR_URI/${ecr_repository_name}:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${database_url}
      - SECRET_KEY=${secret_key}
      - ALGORITHM=${algorithm}
      - ACCESS_TOKEN_EXPIRE_MINUTES=${access_token_expire_minutes}
      - PROJECT_NAME=${project_name}
      - VERSION=${version}
      - ENVIRONMENT=${environment}
      - DEBUG=${debug}
      - LOG_LEVEL=${log_level}
      - CORS_ORIGINS='${cors_origins}'
      - ALLOWED_HOSTS='${allowed_hosts}'
      - RATE_LIMIT_CALLS=${rate_limit_calls}
      - RATE_LIMIT_PERIOD=${rate_limit_period}
      - OTP_SECRET=${otp_secret}
      - OTP_EXPIRY_MINUTES=${otp_expiry_minutes}
      - AWS_ACCESS_KEY_ID=${aws_access_key_id}
      - AWS_SECRET_ACCESS_KEY=${aws_secret_access_key}
      - AWS_REGION=${aws_region}
      - S3_BUCKET_NAME=${s3_bucket_name}
      - UPSTASH_REDIS_URL=${upstash_redis_url}
      - UPSTASH_REDIS_TOKEN=${upstash_redis_token}
      - REDIS_USER_CACHE_TTL=${redis_user_cache_ttl}
      - REDIS_BLACKLIST_TTL=${redis_blacklist_ttl}
      - AWS_SES_FROM_EMAIL=${aws_ses_from_email}
      - AWS_SES_REGION=${aws_ses_region}
      - AWS_DEFAULT_REGION=${aws_default_region}
    restart: always
    networks:
      - default

networks:
  default:
    driver: bridge

EOF

# Create deployment status script
cat <<'EOF' > /home/ubuntu/deployment-status.sh
#!/bin/bash
# Deployment status monitoring script

STATUS_FILE="/home/ubuntu/deployment.status"
LOG_FILE="/home/ubuntu/deployment.log"

echo "$(date): Starting deployment" >> $LOG_FILE
echo "DEPLOYING" > $STATUS_FILE

# Start the app with environment variables
docker-compose -f /home/ubuntu/docker-compose.yml up -d

# Wait for health check to pass
echo "$(date): Waiting for application to be healthy" >> $LOG_FILE
RETRIES=0
MAX_RETRIES=30

while [ $RETRIES -lt $MAX_RETRIES ]; do
    if curl -f http://localhost:8000/health >/dev/null 2>&1; then
        echo "$(date): Application is healthy" >> $LOG_FILE
        echo "HEALTHY" > $STATUS_FILE
        exit 0
    fi
    
    echo "$(date): Health check failed, retry $((RETRIES + 1))/$MAX_RETRIES" >> $LOG_FILE
    sleep 10
    RETRIES=$((RETRIES + 1))
done

echo "$(date): Deployment failed - health checks not passing" >> $LOG_FILE
echo "FAILED" > $STATUS_FILE
exit 1
EOF

chmod +x /home/ubuntu/deployment-status.sh

# Start the deployment
/home/ubuntu/deployment-status.sh

# Create graceful shutdown script
cat <<'EOF' > /home/ubuntu/graceful-shutdown.sh
#!/bin/bash
# Graceful shutdown script for rolling deployments

echo "$(date): Starting graceful shutdown" >> /home/ubuntu/deployment.log

# Stop accepting new connections by removing from nginx upstream
# For now, just stop the containers gracefully
docker-compose -f /home/ubuntu/docker-compose.yml down --timeout 30

echo "$(date): Graceful shutdown completed" >> /home/ubuntu/deployment.log
EOF

chmod +x /home/ubuntu/graceful-shutdown.sh