packer {
  required_plugins {
    amazon = {
      version = ">= 1.2.8"
      source  = "github.com/hashicorp/amazon"
    }
  }
}

# Variable definitions
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t4g.small"
}

variable "ami_name_prefix" {
  description = "Prefix for AMI name"
  type        = string
  default     = "turtil-backend"
}

variable "environment" {
  description = "Environment (dev, prod, etc.)"
  type        = string
  default     = "dev"
}

# Variable for specific ARM AMI
variable "source_ami" {
  description = "Source AMI ID for ARM architecture"
  type        = string
  default     = "ami-0f4448044b7b1e09b"
}

# Build configuration
source "amazon-ebs" "turtil_backend" {
  ami_name      = "${var.ami_name_prefix}-${var.environment}-{{timestamp}}"
  instance_type = var.instance_type
  region        = var.aws_region
  source_ami    = var.source_ami
  ssh_username  = "ec2-user"
  
  # AMI settings
  ami_description = "Turtil Backend AMI - ${var.environment} environment (ARM64)"
  
  tags = {
    Name         = "${var.ami_name_prefix}-${var.environment}"
    Environment  = var.environment
    Project      = "turtil-backend"
    Architecture = "arm64"
    BuildTime    = "{{timestamp}}"
    ManagedBy    = "packer"
  }
  
  # Snapshot settings
  snapshot_tags = {
    Name        = "${var.ami_name_prefix}-${var.environment}-snapshot"
    Environment = var.environment
    Project     = "turtil-backend"
    ManagedBy   = "packer"
  }
}

# Build steps
build {
  name = "turtil-backend-ami"
  sources = [
    "source.amazon-ebs.turtil_backend"
  ]

  # Update system packages
  provisioner "shell" {
    inline = [
      "sudo dnf update -y",
      "sudo dnf install -y git curl wget unzip"
    ]
  }

  # Install Docker
  provisioner "shell" {
    script = "scripts/install-docker.sh"
  }

  # Copy application files
  provisioner "file" {
    source      = "../"
    destination = "/tmp/turtil-backend"
  }

  # Setup application
  provisioner "shell" {
    script = "scripts/setup-app.sh"
  }

  # Copy production configuration files
  provisioner "file" {
    source      = "files/docker-compose.prod.yml"
    destination = "/home/ec2-user/docker-compose.yml"
  }

  provisioner "file" {
    source      = "files/app.service"
    destination = "/tmp/app.service"
  }

  provisioner "file" {
    source      = "files/start.sh"
    destination = "/home/ec2-user/start.sh"
  }

  # Final setup and service configuration
  provisioner "shell" {
    inline = [
      # Move systemd service file
      "sudo mv /tmp/app.service /etc/systemd/system/turtil-backend.service",
      
      # Make start script executable
      "chmod +x /home/ec2-user/start.sh",
      
      # Set ownership
      "sudo chown -R ec2-user:ec2-user /home/ec2-user/",
      
      # Enable the service
      "sudo systemctl enable turtil-backend.service",
      
      # Reload systemd
      "sudo systemctl daemon-reload",
      
      # Clean up temporary files
      "sudo rm -rf /tmp/turtil-backend",
      
      # Clean package cache
      "sudo dnf clean all"
    ]
  }
}