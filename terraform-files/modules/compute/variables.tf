variable "environment" {
  description = "Environment name (dev, test, prod)"
  type        = string
}

variable "custom_ami_id" {
  description = "Custom AMI ID"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t4g.medium"
}

variable "min_size" {
  description = "Minimum number of instances in ASG"
  type        = number
  default     = 1
}

variable "max_size" {
  description = "Maximum number of instances in ASG"
  type        = number
  default     = 2
}

variable "desired_capacity" {
  description = "Desired number of instances in ASG"
  type        = number
  default     = 1
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "public_subnet_ids" {
  description = "List of public subnet IDs for ALB"
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for instances"
  type        = list(string)
}

variable "alb_security_group_id" {
  description = "Security Group ID for ALB"
  type        = string
}

variable "ec2_security_group_id" {
  description = "Security Group ID for EC2 instances"
  type        = string
}

# Application Configuration
variable "database_url" {
  description = "Database connection URL"
  type        = string
  sensitive   = true
}

variable "s3_bucket_name" {
  description = "S3 bucket name"
  type        = string
}

variable "ecr_repository_url" {
  description = "ECR repository URL"
  type        = string
}

variable "secret_key" {
  description = "Application secret key"
  type        = string
  sensitive   = true
}


variable "aws_access_key_id" {
  description = "AWS access key ID"
  type        = string
  sensitive   = true
}

variable "aws_secret_access_key" {
  description = "AWS secret access key"
  type        = string
  sensitive   = true
}

variable "upstash_redis_url" {
  description = "Upstash Redis URL"
  type        = string
  sensitive   = true
}

variable "upstash_redis_token" {
  description = "Upstash Redis token"
  type        = string
  sensitive   = true
}

variable "aws_ses_from_email" {
  description = "AWS SES from email address"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}