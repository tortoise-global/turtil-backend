# Infrastructure Outputs - Auto-populated to GitHub Secrets

output "database_url" {
  description = "Database connection URL"
  value       = module.rds.database_url
  sensitive   = true
}

output "s3_bucket_name" {
  description = "S3 bucket name"
  value       = module.storage.bucket_name
}

output "alb_dns_name" {
  description = "Application Load Balancer DNS name"
  value       = module.compute.alb_dns_name
}

output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = module.ecr.repository_url
}

output "custom_ami_id" {
  description = "Custom AMI ID created for this environment"
  value       = module.ami.ami_id
}

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "asg_name" {
  description = "Auto Scaling Group name"
  value       = module.compute.asg_name
}

# Resource Names for Reference
output "resource_summary" {
  description = "Summary of created resources"
  value = {
    database_name    = "turtil-backend-dev"
    s3_bucket       = module.storage.bucket_name
    alb_name        = "turtil-backend-dev-alb"
    vpc_name        = "turtil-backend-dev-vpc"
    environment     = "dev"
    region          = var.aws_region
  }
}