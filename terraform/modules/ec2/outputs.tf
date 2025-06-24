# ============================================================================
# EC2 MODULE OUTPUTS
# ============================================================================

# Environment Information
output "deployment_mode" {
  description = "Deployment mode (single-instance or auto-scaling-group)"
  value       = var.enable_single_instance ? "single-instance" : "auto-scaling-group"
}

# Network Information
output "vpc_id" {
  description = "VPC ID"
  value       = data.aws_vpc.default.id
}

output "availability_zones" {
  description = "Available zones"
  value       = data.aws_availability_zones.available.names
}

output "subnet_ids" {
  description = "Subnet IDs in the VPC"
  value       = data.aws_subnets.default.ids
}

output "security_group_id" {
  description = "Application security group ID"
  value       = aws_security_group.app.id
}

# Single Instance Outputs (Development)
output "instance_id" {
  description = "EC2 instance ID (single instance mode only)"
  value       = var.enable_single_instance ? aws_instance.single[0].id : null
}

output "instance_public_ip" {
  description = "Public IP address of the instance (single instance mode only)"
  value       = var.enable_single_instance ? aws_instance.single[0].public_ip : null
}

output "instance_private_ip" {
  description = "Private IP address of the instance (single instance mode only)"
  value       = var.enable_single_instance ? aws_instance.single[0].private_ip : null
}

output "instance_public_dns" {
  description = "Public DNS name of the instance (single instance mode only)"
  value       = var.enable_single_instance ? aws_instance.single[0].public_dns : null
}

# Auto Scaling Group Outputs (Test/Production)
output "asg_name" {
  description = "Auto Scaling Group name (ASG mode only)"
  value       = var.enable_single_instance ? null : aws_autoscaling_group.app[0].name
}

output "asg_arn" {
  description = "Auto Scaling Group ARN (ASG mode only)"
  value       = var.enable_single_instance ? null : aws_autoscaling_group.app[0].arn
}

output "launch_template_id" {
  description = "Launch template ID"
  value       = aws_launch_template.app.id
}

output "launch_template_version" {
  description = "Launch template version"
  value       = aws_launch_template.app.latest_version
}

# IAM Information
output "iam_role_arn" {
  description = "IAM role ARN for instances"
  value       = aws_iam_role.app_role.arn
}

output "iam_instance_profile_name" {
  description = "IAM instance profile name"
  value       = aws_iam_instance_profile.app_profile.name
}

# Access Information
output "access_info" {
  description = "Access information for the deployment"
  value = var.enable_single_instance ? {
    mode        = "single-instance"
    public_ip   = aws_instance.single[0].public_ip
    health_url  = "http://${aws_instance.single[0].public_ip}:8000/health"
    app_url     = "http://${aws_instance.single[0].public_ip}:8000"
    ssh_command = "ssh -i your-key.pem ubuntu@${aws_instance.single[0].public_ip}"
  } : {
    mode         = "auto-scaling-group"
    asg_name     = aws_autoscaling_group.app[0].name
    min_size     = aws_autoscaling_group.app[0].min_size
    max_size     = aws_autoscaling_group.app[0].max_size
    desired_size = aws_autoscaling_group.app[0].desired_capacity
  }
}

# Cost Information
output "cost_estimation" {
  description = "Estimated monthly cost"
  value = {
    instance_type = var.instance_type
    spot_enabled  = var.enable_spot_instances
    estimated_cost = var.enable_single_instance ? (
      var.enable_spot_instances ? "$3-5/month (spot)" : "$8-12/month (on-demand)"
    ) : (
      var.enable_spot_instances ? "$15-25/month (spot)" : "$30-50/month (on-demand)"
    )
  }
}