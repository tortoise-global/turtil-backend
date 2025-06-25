# AMI Creation Module - Create if not exists, skip if exists

# Check if AMI with specific tag exists
data "aws_ami" "existing_ami" {
  most_recent = true
  owners      = ["self"]
  
  filter {
    name   = "tag:Name"
    values = ["turtil-backend-${var.environment}-ami"]
  }
  
  filter {
    name   = "tag:Environment"
    values = [var.environment]
  }
  
  filter {
    name   = "state"
    values = ["available"]
  }
}

# Get base Ubuntu AMI for ARM64
data "aws_ami" "ubuntu_base" {
  most_recent = true
  owners      = ["099720109477"] # Canonical
  
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-arm64-server-*"]
  }
  
  filter {
    name   = "architecture"
    values = ["arm64"]
  }
  
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Get default VPC and subnet for AMI creation
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  
  filter {
    name   = "map-public-ip-on-launch"
    values = ["true"]
  }
}

# Security group for AMI creation (SSH access)
resource "aws_security_group" "ami_creation" {
  count = data.aws_ami.existing_ami.id == null ? 1 : 0
  
  name_prefix = "turtil-backend-${var.environment}-ami-creation"
  description = "Security group for AMI creation - SSH access"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "turtil-backend-${var.environment}-ami-creation-sg"
  })
}

# Key pair for AMI creation
resource "aws_key_pair" "ami_creation" {
  count = data.aws_ami.existing_ami.id == null ? 1 : 0
  
  key_name   = "turtil-backend-${var.environment}-ami-key"
  public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC7vK8F8W9wX6H+2gKXRzqq9FpXZp2F8d9X4K3nZ1z8cW2x7Yz4b5p6qN3m8K9x1z2v3n4M5b6c7d8e9f0a1s2d3f4g5h6j7k8l9" # Temporary - will be replaced

  tags = merge(var.tags, {
    Name = "turtil-backend-${var.environment}-ami-key"
  })
}

# User data script for AMI preparation
locals {
  ami_preparation_script = base64encode(templatefile("${path.module}/user_data.sh", {
    environment = var.environment
  }))
}

# EC2 instance for AMI creation (only if AMI doesn't exist)
resource "aws_instance" "ami_builder" {
  count = data.aws_ami.existing_ami.id == null ? 1 : 0
  
  ami                    = data.aws_ami.ubuntu_base.id
  instance_type         = "t4g.micro"
  key_name              = aws_key_pair.ami_creation[0].key_name
  vpc_security_group_ids = [aws_security_group.ami_creation[0].id]
  subnet_id             = data.aws_subnets.default.ids[0]
  
  user_data = local.ami_preparation_script
  
  root_block_device {
    volume_type = "gp3"
    volume_size = 20
    encrypted   = true
  }
  
  tags = merge(var.tags, {
    Name    = "turtil-backend-${var.environment}-ami-builder"
    Purpose = "ami-creation"
  })
  
  # Wait for user data script to complete
  provisioner "remote-exec" {
    inline = [
      "cloud-init status --wait",
      "sudo systemctl is-active docker",
      "docker --version"
    ]
    
    connection {
      type        = "ssh"
      user        = "ubuntu"
      private_key = tls_private_key.ami_creation[0].private_key_pem
      host        = self.public_ip
    }
  }
}

# Generate private key for SSH
resource "tls_private_key" "ami_creation" {
  count = data.aws_ami.existing_ami.id == null ? 1 : 0
  
  algorithm = "RSA"
  rsa_bits  = 4096
}

# Update key pair with generated public key
resource "aws_key_pair" "ami_creation_updated" {
  count = data.aws_ami.existing_ami.id == null ? 1 : 0
  
  key_name   = aws_key_pair.ami_creation[0].key_name
  public_key = tls_private_key.ami_creation[0].public_key_openssh
  
  depends_on = [aws_key_pair.ami_creation]
}

# Create AMI from prepared instance
resource "aws_ami_from_instance" "custom_ami" {
  count = data.aws_ami.existing_ami.id == null ? 1 : 0
  
  name                    = "turtil-backend-${var.environment}-ami-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
  description             = "Custom AMI for turtil-backend ${var.environment} environment with Docker pre-installed"
  source_instance_id      = aws_instance.ami_builder[0].id
  snapshot_without_reboot = false
  
  tags = merge(var.tags, {
    Name         = "turtil-backend-${var.environment}-ami"
    Environment  = var.environment
    Project      = "turtil-backend"
    Architecture = "arm64"
    OS          = "ubuntu-22.04"
    CreatedBy   = "terraform"
  })
  
  depends_on = [aws_instance.ami_builder]
}

# Clean up temporary resources after AMI creation
resource "null_resource" "cleanup" {
  count = data.aws_ami.existing_ami.id == null ? 1 : 0
  
  provisioner "local-exec" {
    command = <<-EOT
      # Terminate the AMI builder instance after AMI is created
      aws ec2 terminate-instances --region ${var.region} --instance-ids ${aws_instance.ami_builder[0].id}
      
      # Delete the temporary key pair
      aws ec2 delete-key-pair --region ${var.region} --key-name ${aws_key_pair.ami_creation[0].key_name}
      
      # Delete the temporary security group (wait for instance termination)
      sleep 60
      aws ec2 delete-security-group --region ${var.region} --group-id ${aws_security_group.ami_creation[0].id}
    EOT
  }
  
  depends_on = [aws_ami_from_instance.custom_ami]
}