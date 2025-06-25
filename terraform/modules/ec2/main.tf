# ============================================================================
# EC2 MODULE - Compute Instances
# ============================================================================

data "aws_caller_identity" "current" {}

# EC2 Instance
resource "aws_instance" "main" {
  ami           = var.ami_id
  instance_type = var.instance_type
  key_name      = var.key_name
  
  subnet_id              = var.subnet_id
  vpc_security_group_ids = var.security_group_ids
  iam_instance_profile   = var.iam_instance_profile_name
  
  # User data for instance initialization
  user_data = var.user_data_script != null ? base64encode(templatefile(var.user_data_script, var.user_data_vars)) : null
  
  # Root volume configuration
  root_block_device {
    volume_type = var.root_volume_type
    volume_size = var.root_volume_size
    encrypted   = var.root_volume_encrypted
    
    tags = {
      Name        = "${var.project_name}-${var.environment}-root-volume"
      Environment = var.environment
      Project     = var.project_name
    }
  }
  
  # Additional EBS volumes
  dynamic "ebs_block_device" {
    for_each = var.additional_volumes
    content {
      device_name = ebs_block_device.value.device_name
      volume_type = ebs_block_device.value.volume_type
      volume_size = ebs_block_device.value.volume_size
      encrypted   = ebs_block_device.value.encrypted
      
      tags = {
        Name        = "${var.project_name}-${var.environment}-${ebs_block_device.value.name}"
        Environment = var.environment
        Project     = var.project_name
      }
    }
  }
  
  # Instance metadata options
  metadata_options {
    http_endpoint               = var.metadata_http_endpoint
    http_tokens                = var.metadata_http_tokens
    http_put_response_hop_limit = var.metadata_http_put_response_hop_limit
    instance_metadata_tags     = var.instance_metadata_tags
  }
  
  # Monitoring
  monitoring = var.detailed_monitoring
  
  # Placement
  availability_zone = var.availability_zone
  tenancy          = var.tenancy
  
  # Credit specification for burstable instances
  dynamic "credit_specification" {
    for_each = can(regex("^t[2-4]", var.instance_type)) ? [1] : []
    content {
      cpu_credits = var.cpu_credits
    }
  }
  
  tags = merge(
    {
      Name        = "${var.project_name}-${var.environment}"
      Environment = var.environment
      Project     = var.project_name
    },
    var.additional_tags
  )
  
  lifecycle {
    ignore_changes = [
      ami,
      user_data
    ]
  }
}

# Elastic IP (optional)
resource "aws_eip" "main" {
  count = var.associate_elastic_ip ? 1 : 0
  
  instance = aws_instance.main.id
  domain   = "vpc"
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-eip"
    Environment = var.environment
    Project     = var.project_name
  }
  
  depends_on = [aws_instance.main]
}

# CloudWatch alarms (optional)
resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  count = var.enable_cloudwatch_alarms ? 1 : 0
  
  alarm_name          = "${var.project_name}-${var.environment}-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Average"
  threshold           = var.cpu_alarm_threshold
  alarm_description   = "This metric monitors ec2 cpu utilization"
  
  dimensions = {
    InstanceId = aws_instance.main.id
  }
  
  alarm_actions = var.alarm_actions
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-cpu-alarm"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_cloudwatch_metric_alarm" "status_check" {
  count = var.enable_cloudwatch_alarms ? 1 : 0
  
  alarm_name          = "${var.project_name}-${var.environment}-status-check"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "StatusCheckFailed"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Maximum"
  threshold           = "0"
  alarm_description   = "This metric monitors ec2 status check"
  
  dimensions = {
    InstanceId = aws_instance.main.id
  }
  
  alarm_actions = var.alarm_actions
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-status-alarm"
    Environment = var.environment
    Project     = var.project_name
  }
}