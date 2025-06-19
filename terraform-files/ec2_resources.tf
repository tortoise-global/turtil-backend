# Load balancer
module "example_alb" {
  source            = "./modules/load_balancers"
  alb_name          = var.alb_name[terraform.workspace]
  target_group_port = var.alb_target_group_port[terraform.workspace]
  health_check_path = var.alb_health_check_path[terraform.workspace]
  ec2_instance_id   = null # Not needed with ASG
  tags = {
    Environment = lookup(var.ec2_env_tags, terraform.workspace)
  }
}

# Data source to find the latest Ubuntu AMI
data "aws_ami" "ubuntu" {
  most_recent = true

  filter {
    name   = "name"
    values = [var.ec2_ami_name_filter[terraform.workspace]]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "architecture"
    values = [var.ec2_architecture[terraform.workspace]]
  }

  owners = [var.ec2_ami_owner[terraform.workspace]]

  # Debugging output for AMI search
  lifecycle {
    postcondition {
      condition     = length(self.id) > 0
      error_message = "No AMI found matching filters: name=${var.ec2_ami_name_filter[terraform.workspace]}, architecture=${var.ec2_architecture[terraform.workspace]}, owner=${var.ec2_ami_owner[terraform.workspace]}. Verify filters and region (ap-south-1)."
    }
  }
}

# Security Group for EC2 instances
resource "aws_security_group" "ec2_sg" {
  name        = "${terraform.workspace}-cms-api-sg"
  description = "Security group for CMS FastAPI EC2 instances"
  vpc_id      = data.aws_vpc.this.id

  dynamic "ingress" {
    for_each = var.ec2_ingress_rules[terraform.workspace]
    content {
      description = ingress.value.description
      from_port   = ingress.value.from_port
      to_port     = ingress.value.to_port
      protocol    = ingress.value.protocol
      cidr_blocks = [ingress.value.cidr_block]
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Environment = lookup(var.ec2_env_tags, terraform.workspace)
    Name        = "${terraform.workspace}-cms-api-sg"
  }
}

# Launch Template for ASG
resource "aws_launch_template" "cms_fast_api" {
  name          = "${terraform.workspace}-cms-api-lt"
  image_id      = data.aws_ami.ubuntu.id
  instance_type = var.ec2_instance_type[terraform.workspace]
  key_name      = var.ec2_key_name[terraform.workspace]

  iam_instance_profile {
    name = aws_iam_instance_profile.ec2_ecr_access.name
  }

  network_interfaces {
    associate_public_ip_address = true
    security_groups             = [aws_security_group.ec2_sg.id, module.example_alb.security_group_id]
  }

  block_device_mappings {
    device_name = "/dev/sda1"
    ebs {
      volume_size = var.ec2_root_block_device_size[terraform.workspace]
      volume_type = "gp3"
      encrypted   = true
    }
  }

  user_data = base64encode(templatefile("${path.module}/user_data.tpl", {
    database_url                = var.app_database_url
    secret_key                  = var.app_secret_key
    algorithm                   = var.app_algorithm
    access_token_expire_minutes = var.app_access_token_expire_minutes
    project_name                = var.app_project_name
    version                     = var.app_version
    environment                 = var.app_environment
    debug                       = var.app_debug
    log_level                   = var.app_log_level
    rate_limit_calls            = var.app_rate_limit_calls
    rate_limit_period           = var.app_rate_limit_period
    otp_secret                  = var.app_otp_secret
    otp_expiry_minutes          = var.app_otp_expiry_minutes
    aws_access_key_id           = var.app_aws_access_key_id
    aws_secret_access_key       = var.app_aws_secret_access_key
    s3_bucket_name              = var.app_s3_bucket_name
    upstash_redis_url           = var.app_upstash_redis_url
    upstash_redis_token         = var.app_upstash_redis_token
    redis_user_cache_ttl        = var.app_redis_user_cache_ttl
    redis_blacklist_ttl         = var.app_redis_blacklist_ttl
    aws_ses_from_email          = var.app_aws_ses_from_email
    aws_ses_region              = var.app_aws_ses_region
    aws_default_region          = var.app_aws_default_region
    aws_region                  = var.app_aws_region
    cors_origins                = var.app_cors_origins
    allowed_hosts               = var.app_allowed_hosts
    ecr_account_id              = var.ecr_account_id
    ecr_repository_name         = var.ecr_repository_name
  }))

  tags = {
    Environment = lookup(var.ec2_env_tags, terraform.workspace)
  }
}

# Auto Scaling Group
resource "aws_autoscaling_group" "cms_fast_api" {
  name                = "${terraform.workspace}-cms-api-asg"
  min_size            = var.asg_min_size[terraform.workspace]
  desired_capacity    = var.asg_desired_capacity[terraform.workspace]
  max_size            = var.asg_max_size[terraform.workspace]
  vpc_zone_identifier = data.aws_subnets.this.ids
  target_group_arns   = [module.example_alb.target_group_arn]

  launch_template {
    id      = aws_launch_template.cms_fast_api.id
    version = "$Latest"
  }

  tag {
    key                 = "Environment"
    value               = lookup(var.ec2_env_tags, terraform.workspace)
    propagate_at_launch = true
  }

  tag {
    key                 = "Name"
    value               = "${terraform.workspace}-cms-api-asg-instance"
    propagate_at_launch = true
  }
}

# Scaling Policy for ASG (Target Tracking based on CPU Utilization)
resource "aws_autoscaling_policy" "cms_fast_api_target_tracking" {
  name                   = "${terraform.workspace}-cms-api-target-tracking"
  autoscaling_group_name = aws_autoscaling_group.cms_fast_api.name
  policy_type            = "TargetTrackingScaling"

  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ASGAverageCPUUtilization"
    }
    target_value = var.asg_target_cpu_utilization[terraform.workspace]
  }
}

# Subnets for ASG (ap-south-1a, ap-south-1b)
data "aws_vpc" "this" {
  default = true
}

data "aws_subnets" "this" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.this.id]
  }
  filter {
    name   = "availability-zone"
    values = ["ap-south-1a", "ap-south-1b"]
  }
}

# CloudFront
module "cloudfront_with_alb" {
  source              = "./modules/cloudfront"
  distribution_name   = "${var.cloudfront_distribution_name[terraform.workspace]}-alb"
  alb_dns_name        = module.example_alb.alb_dns_name
  domain_name         = var.cloudfront_domain_name[terraform.workspace]
  route53_zone_id     = var.cloudfront_route53_zone_id[terraform.workspace]
  acm_certificate_arn = local.acm_certificate_arn
  default_root_object = ""
  tags = {
    Environment = lookup(var.ec2_env_tags, terraform.workspace)
  }
}

# Outputs
output "example_alb_dns_name" {
  value = module.example_alb.alb_dns_name
}

output "example_alb_arn" {
  value = module.example_alb.alb_dns_name
}

output "example_alb_target_group_arn" {
  value = module.example_alb.target_group_arn
}

output "cloudfront_with_alb_domain_name" {
  value = module.cloudfront_with_alb.cloudfront_domain_name
}

output "asg_name" {
  value = aws_autoscaling_group.cms_fast_api.name
}


