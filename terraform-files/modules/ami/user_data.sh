#!/bin/bash

# AMI Preparation Script for turtil-backend
# Environment: ${environment}

set -e

exec > /var/log/ami-preparation.log 2>&1

echo "$(date): Starting AMI preparation for ${environment} environment..."

# Update system packages
apt update -y
apt upgrade -y

# Install essential packages
apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    unzip \
    nginx \
    htop \
    vim \
    git \
    software-properties-common \
    amazon-ecr-credential-helper \
    awscli

# Install Docker Engine for ARM64
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=arm64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt update -y
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Install docker-compose (standalone)
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Configure Docker
systemctl enable docker
systemctl start docker
usermod -aG docker ubuntu

# Configure nginx
systemctl enable nginx

# Set up Docker log rotation
tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF

# Restart Docker to apply configuration
systemctl restart docker

# Configure ECR credential helper
mkdir -p /root/.docker
mkdir -p /home/ubuntu/.docker
echo '{"credsStore": "ecr-login"}' | tee /root/.docker/config.json
echo '{"credsStore": "ecr-login"}' | tee /home/ubuntu/.docker/config.json
chown ubuntu:ubuntu /home/ubuntu/.docker/config.json

# Clean up package cache and temporary files
apt autoremove -y
apt autoclean
rm -rf /var/lib/apt/lists/*
rm -rf /tmp/*
rm -rf /var/tmp/*

# Create AMI preparation marker
echo "turtil-backend-${environment}-ami" | tee /etc/ami-info
echo "Prepared on: $(date)" | tee -a /etc/ami-info
echo "Environment: ${environment}" | tee -a /etc/ami-info
echo "Region: ap-south-2" | tee -a /etc/ami-info
echo "Docker version: $(docker --version)" | tee -a /etc/ami-info
echo "Docker Compose version: $(docker-compose --version)" | tee -a /etc/ami-info
echo "AWS CLI version: $(aws --version)" | tee -a /etc/ami-info

# Create ready marker
touch /tmp/ami-ready

echo "$(date): AMI preparation completed successfully for ${environment}!"

# Signal completion
/opt/aws/bin/cfn-signal -e $? --stack ${AWS::StackName} --resource AutoScalingGroup --region ${AWS::Region} || true