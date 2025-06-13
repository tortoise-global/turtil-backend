#!/bin/bash
# Install Docker from official repository
sudo apt-get update -y
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
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

    location / {
        add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS, PUT, DELETE'; 
        add_header 'Access-Control-Allow-Headers' 'Authorization'; 
        add_header 'Access-Control-Allow-Origins' '*'; 
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Test Nginx configuration and reload
sudo nginx -t
sudo systemctl reload nginx

# Pull latest image from ECR (IAM role handles authentication)
ECR_URI="033464272864.dkr.ecr.ap-south-1.amazonaws.com"

aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin $ECR_URI

docker pull $ECR_URI/dev-cms-api-repo:latest

# Generate docker-compose.yml with environment variables
cat <<EOF > /home/ubuntu/docker-compose.yml
services:
  web:
    image: $ECR_URI/dev-cms-api-repo:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${database_url}
      - SECRET_KEY=${secret_key}
      - ALGORITHM=HS256
      - ACCESS_TOKEN_EXPIRE_MINUTES=30
      - PROJECT_NAME=Turtil Backend
      - VERSION=1.0.0
      - ENVIRONMENT=${environment}
      - DEBUG=${debug}
      - LOG_LEVEL=INFO
      - CORS_ORIGINS=["*", "http://localhost:3000", "http://localhost:8080"]
      - ALLOWED_HOSTS=["*", "localhost", "127.0.0.1", "0.0.0.0"]
      - RATE_LIMIT_CALLS=100
      - RATE_LIMIT_PERIOD=60
      - OTP_SECRET=123456
      - OTP_EXPIRY_MINUTES=5
      - AWS_ACCESS_KEY_ID=${aws_access_key_id}
      - AWS_SECRET_ACCESS_KEY=${aws_secret_access_key}
      - AWS_REGION=ap-south-1
      - S3_BUCKET_NAME=${s3_bucket_name}
      - UPSTASH_REDIS_URL=${upstash_redis_url}
      - UPSTASH_REDIS_TOKEN=${upstash_redis_token}
      - REDIS_USER_CACHE_TTL=300
      - REDIS_BLACKLIST_TTL=86400
      - GMAIL_EMAIL=${gmail_email}
      - GMAIL_APP_PASSWORD=${gmail_app_password}
    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
    restart: always
    networks:
      - default

networks:
  default:
    driver: bridge

EOF

# Start the app with environment variables
docker-compose -f /home/ubuntu/docker-compose.yml up -d