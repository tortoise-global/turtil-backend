#!/bin/bash
set -e

echo "Installing Docker and Docker Compose for ARM64 architecture..."

# Detect architecture
ARCH=$(uname -m)
echo "Detected architecture: $ARCH"

# Install Docker
sudo dnf install -y docker

# Start and enable Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add ec2-user to docker group to run docker commands without sudo
sudo usermod -a -G docker ec2-user

# Install Docker Compose (with ARM64 support)
DOCKER_COMPOSE_VERSION="2.24.1"
if [[ "$ARCH" == "aarch64" ]]; then
    COMPOSE_ARCH="aarch64"
elif [[ "$ARCH" == "x86_64" ]]; then
    COMPOSE_ARCH="x86_64"
else
    echo "Unsupported architecture: $ARCH"
    exit 1
fi

echo "Installing Docker Compose v${DOCKER_COMPOSE_VERSION} for ${COMPOSE_ARCH}..."
sudo curl -L "https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-linux-${COMPOSE_ARCH}" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create symlink for docker-compose
sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

# Verify installations
docker --version
docker-compose --version

echo "Docker and Docker Compose installation completed successfully for ${ARCH}!"