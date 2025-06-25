# Compute Module - EC2, ASG, ALB

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "turtil-backend-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.alb_security_group_id]
  subnets            = var.public_subnet_ids
  
  enable_deletion_protection = var.environment == "prod" ? true : false
  
  tags = merge(var.tags, {
    Name = "turtil-backend-${var.environment}-alb"
  })
}

# ALB Target Group
resource "aws_lb_target_group" "main" {
  name     = "turtil-backend-${var.environment}-tg"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = var.vpc_id
  
  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
    port                = "traffic-port"
    protocol            = "HTTP"
  }
  
  tags = merge(var.tags, {
    Name = "turtil-backend-${var.environment}-tg"
  })
}

# ALB Listener
resource "aws_lb_listener" "main" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"
  
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main.arn
  }
}

# Launch Template
resource "aws_launch_template" "main" {
  name_prefix   = "turtil-backend-${var.environment}-"
  description   = "Launch template for turtil-backend ${var.environment}"
  image_id      = var.custom_ami_id
  instance_type = var.instance_type
  
  vpc_security_group_ids = [var.ec2_security_group_id]
  
  iam_instance_profile {
    name = aws_iam_instance_profile.main.name
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
  
  # User data for application setup
  user_data = base64encode(templatefile("${path.module}/user_data.tpl", {
    database_url         = var.database_url
    s3_bucket_name      = var.s3_bucket_name
    ecr_repository_url  = var.ecr_repository_url
    secret_key          = var.secret_key
    aws_access_key_id   = var.aws_access_key_id
    aws_secret_access_key = var.aws_secret_access_key
    upstash_redis_url   = var.upstash_redis_url
    upstash_redis_token = var.upstash_redis_token
    aws_ses_from_email  = var.aws_ses_from_email
    environment         = var.environment
    aws_region          = "ap-south-2"
  }))
  
  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
    http_put_response_hop_limit = 2
  }
  
  monitoring {
    enabled = true
  }
  
  tag_specifications {
    resource_type = "instance"
    tags = merge(var.tags, {
      Name = "turtil-backend-${var.environment}-instance"
    })
  }
  
  lifecycle {
    create_before_destroy = true
  }
}

# Auto Scaling Group
resource "aws_autoscaling_group" "main" {
  name                = "turtil-backend-${var.environment}-asg"
  vpc_zone_identifier = var.private_subnet_ids
  target_group_arns   = [aws_lb_target_group.main.arn]
  
  min_size         = var.min_size
  max_size         = var.max_size
  desired_capacity = var.desired_capacity
  
  health_check_type         = "ELB"
  health_check_grace_period = 120
  default_cooldown         = 150
  
  launch_template {
    id      = aws_launch_template.main.id
    version = "$Latest"
  }
  
  # Instance refresh for zero-downtime deployments
  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage = 50
      instance_warmup        = 90
      checkpoint_delay       = 0
      checkpoint_percentages = [100]
    }
  }
  
  dynamic "tag" {
    for_each = var.tags
    content {
      key                 = tag.key
      value               = tag.value
      propagate_at_launch = true
    }
  }
  
  tag {
    key                 = "Name"
    value               = "turtil-backend-${var.environment}-asg-instance"
    propagate_at_launch = true
  }
}

# Auto Scaling Policy
resource "aws_autoscaling_policy" "target_tracking" {
  name                   = "turtil-backend-${var.environment}-target-tracking"
  autoscaling_group_name = aws_autoscaling_group.main.name
  policy_type            = "TargetTrackingScaling"
  
  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ASGAverageCPUUtilization"
    }
    target_value = 50
  }
}

# IAM Role for EC2 instances
resource "aws_iam_role" "main" {
  name_prefix = "turtil-backend-${var.environment}-ec2-"
  
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

# IAM Policy for ECR, S3, and SES access
resource "aws_iam_role_policy" "app_access" {
  name_prefix = "turtil-backend-${var.environment}-app-access-"
  role        = aws_iam_role.main.id
  
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
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.s3_bucket_name}",
          "arn:aws:s3:::${var.s3_bucket_name}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# Attach SSM managed policy
resource "aws_iam_role_policy_attachment" "ssm_managed_instance_core" {
  role       = aws_iam_role.main.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# IAM Instance Profile
resource "aws_iam_instance_profile" "main" {
  name_prefix = "turtil-backend-${var.environment}-ec2-"
  role        = aws_iam_role.main.name
  
  tags = var.tags
}