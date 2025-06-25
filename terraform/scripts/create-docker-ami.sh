#!/bin/bash

# ============================================================================
# DOCKER-READY AMI PREPARATION SCRIPT
# ============================================================================
# This script prepares an Ubuntu 24.04 LTS instance for AMI creation
# with Docker, docker-compose, nginx, and all required tools pre-installed

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

print_info "Starting Docker-ready AMI preparation..."
print_info "Target: Ubuntu 24.04 LTS ARM64 with Docker, docker-compose, nginx"

# Update system packages
print_info "Updating system packages..."
sudo apt update -y
sudo apt upgrade -y

# Install essential packages
print_info "Installing essential packages..."
sudo apt install -y \
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
    software-properties-common

# Install Docker Engine
print_info "Installing Docker Engine..."
# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=arm64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update package index
sudo apt update -y

# Install Docker Engine
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Install docker-compose (standalone)
print_info "Installing docker-compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Configure Docker
print_info "Configuring Docker..."
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker ubuntu

# Install AWS CLI v2
print_info "Installing AWS CLI v2..."
curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
rm -rf aws awscliv2.zip

# Configure nginx
print_info "Configuring nginx..."
sudo systemctl enable nginx

# Create docker-compose bash completion
print_info "Setting up bash completion..."
sudo curl -L https://raw.githubusercontent.com/docker/compose/master/contrib/completion/bash/docker-compose -o /etc/bash_completion.d/docker-compose

# Set up log rotation for Docker
print_info "Configuring Docker log rotation..."
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF

# Clean up package cache and temporary files
print_info "Cleaning up system..."
sudo apt autoremove -y
sudo apt autoclean
sudo rm -rf /var/lib/apt/lists/*
sudo rm -rf /tmp/*
sudo rm -rf /var/tmp/*

# Clear bash history
history -c
echo "" > ~/.bash_history

# Create AMI preparation marker
print_info "Creating AMI preparation marker..."
echo "turtil-backend-docker-ubuntu-24.04-arm64" | sudo tee /etc/ami-info
echo "Prepared on: $(date)" | sudo tee -a /etc/ami-info
echo "Docker version: $(docker --version)" | sudo tee -a /etc/ami-info
echo "Docker Compose version: $(docker-compose --version)" | sudo tee -a /etc/ami-info
echo "AWS CLI version: $(aws --version)" | sudo tee -a /etc/ami-info

# Verify installations
print_info "Verifying installations..."
docker --version
docker-compose --version
aws --version
nginx -v

print_success "AMI preparation completed successfully!"
print_warning "Next steps:"
echo "1. Stop this EC2 instance"
echo "2. Create AMI from this instance"
echo "3. Tag the AMI with: Name=turtil-backend-docker-ubuntu-24.04-arm64"
echo "4. Update environment files with the new AMI ID"

print_info "Instance is ready for AMI creation. You can now stop the instance."