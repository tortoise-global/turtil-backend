# ============================================================================
# EC2 MODULE - DUAL MODE: SINGLE INSTANCE OR AUTO SCALING GROUP
# ============================================================================
# Supports both single EC2 instance (dev) and Auto Scaling Group (test/prod)

# Data sources
data "aws_region" "current" {}

data "aws_caller_identity" "current" {}

# Get default VPC
data "aws_vpc" "default" {
  default = true
}

# Get availability zones
data "aws_availability_zones" "available" {
  state = "available"
}

# Get subnets in default VPC
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Get latest Ubuntu 22.04 ARM64 AMI for ARM instances
data "aws_ami" "ubuntu_arm64" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-arm64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Security Group for instances
resource "aws_security_group" "app" {
  name_prefix = "${var.project_name}-${var.environment}-app-"
  description = "Security group for ${var.project_name} ${var.environment} application"
  vpc_id      = data.aws_vpc.default.id

  # SSH access
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Application port (for development direct access)
  ingress {
    description = "Application"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = var.environment == "dev" ? ["0.0.0.0/0"] : []
  }

  # HTTP for ALB health checks and traffic
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS
  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
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
    Name = "${var.project_name}-${var.environment}-app-sg"
  })
}

# IAM role for EC2 instances
resource "aws_iam_role" "app_role" {
  name = "${var.project_name}-${var.environment}-app-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# IAM policy for ECR and S3 access
resource "aws_iam_role_policy" "app_policy" {
  name = "${var.project_name}-${var.environment}-app-policy"
  role = aws_iam_role.app_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "arn:aws:s3:::${var.project_name}-${var.environment}-*/*"
      }
    ]
  })
}

# IAM instance profile
resource "aws_iam_instance_profile" "app_profile" {
  name = "${var.project_name}-${var.environment}-app-profile"
  role = aws_iam_role.app_role.name

  tags = var.tags
}

# User data script for application setup
locals {
  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    project_name                    = var.project_name
    environment                     = var.environment
    aws_region                      = var.aws_region
    ecr_account_id                  = var.ecr_account_id
    app_database_url               = var.app_database_url
    app_secret_key                 = var.app_secret_key
    app_algorithm                  = var.app_algorithm
    app_access_token_expire_minutes = var.app_access_token_expire_minutes
    app_version                    = var.app_version
    app_debug                      = var.app_debug
    app_log_level                  = var.app_log_level
    app_rate_limit_calls           = var.app_rate_limit_calls
    app_rate_limit_period          = var.app_rate_limit_period
    app_otp_expiry_minutes         = var.app_otp_expiry_minutes
    app_aws_access_key_id          = var.app_aws_access_key_id
    app_aws_secret_access_key      = var.app_aws_secret_access_key
    app_upstash_redis_url          = var.app_upstash_redis_url
    app_upstash_redis_token        = var.app_upstash_redis_token
    app_redis_user_cache_ttl       = var.app_redis_user_cache_ttl
    app_redis_blacklist_ttl        = var.app_redis_blacklist_ttl
    app_aws_ses_from_email         = var.app_aws_ses_from_email
    app_aws_ses_region             = var.app_aws_ses_region
  }))
}

# Launch Template for both single instance and ASG
resource "aws_launch_template" "app" {
  name_prefix   = "${var.project_name}-${var.environment}-"
  image_id      = data.aws_ami.ubuntu_arm64.id
  instance_type = var.instance_type
  key_name      = null # No SSH key needed for now

  vpc_security_group_ids = [aws_security_group.app.id]

  iam_instance_profile {
    name = aws_iam_instance_profile.app_profile.name
  }

  user_data = local.user_data

  # Spot instance configuration
  dynamic "instance_market_options" {
    for_each = var.enable_spot_instances ? [1] : []
    content {
      market_type = "spot"
      spot_options {
        spot_instance_type = "one-time"
      }
    }
  }

  block_device_mappings {
    device_name = "/dev/sda1"
    ebs {
      volume_size = 20
      volume_type = "gp3"
      encrypted   = true
      throughput  = 125
      iops        = 3000
    }
  }

  monitoring {
    enabled = true
  }

  tags = var.tags

  tag_specifications {
    resource_type = "instance"
    tags = merge(var.tags, {
      Name = "${var.project_name}-${var.environment}"
    })
  }

  lifecycle {
    create_before_destroy = true
  }
}

# =============================================================================
# SINGLE INSTANCE MODE (Development)
# =============================================================================
resource "aws_instance" "single" {
  count = var.enable_single_instance ? 1 : 0

  launch_template {
    id      = aws_launch_template.app.id
    version = "$Latest"
  }

  subnet_id                   = data.aws_subnets.default.ids[0]
  associate_public_ip_address = true

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-single"
    Mode = "single-instance"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# =============================================================================
# AUTO SCALING GROUP MODE (Test/Production)
# =============================================================================
resource "aws_autoscaling_group" "app" {
  count = var.enable_single_instance ? 0 : 1

  name                = "${var.project_name}-${var.environment}-asg"
  vpc_zone_identifier = data.aws_subnets.default.ids
  min_size            = var.min_size
  max_size            = var.max_size
  desired_capacity    = var.desired_capacity
  health_check_type   = "EC2"
  health_check_grace_period = 300

  launch_template {
    id      = aws_launch_template.app.id
    version = "$Latest"
  }

  # Instance refresh configuration for zero-downtime deployments
  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage = 50
      instance_warmup        = 300
    }
  }

  tag {
    key                 = "Name"
    value               = "${var.project_name}-${var.environment}-asg"
    propagate_at_launch = false
  }

  dynamic "tag" {
    for_each = var.tags
    content {
      key                 = tag.key
      value               = tag.value
      propagate_at_launch = true
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}