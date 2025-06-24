# ============================================================================
# EC2 MODULE VARIABLES
# ============================================================================
# Variables for EC2 instances and Auto Scaling Groups

# Environment Configuration
variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, test, prod)"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

# Instance Configuration
variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t4g.micro"
}

variable "enable_single_instance" {
  description = "Whether to use single EC2 instance instead of Auto Scaling Group"
  type        = bool
  default     = false
}

variable "enable_spot_instances" {
  description = "Whether to use spot instances"
  type        = bool
  default     = false
}

# Auto Scaling Configuration (when not using single instance)
variable "min_size" {
  description = "Minimum number of instances in Auto Scaling Group"
  type        = number
  default     = 1
}

variable "max_size" {
  description = "Maximum number of instances in Auto Scaling Group"
  type        = number
  default     = 3
}

variable "desired_capacity" {
  description = "Desired number of instances in Auto Scaling Group"
  type        = number
  default     = 1
}

# Application Environment Variables
variable "ecr_account_id" {
  description = "AWS Account ID for ECR"
  type        = string
}

variable "app_database_url" {
  description = "Database URL for the application"
  type        = string
  sensitive   = true
}

variable "app_secret_key" {
  description = "Secret key for the application"
  type        = string
  sensitive   = true
}

variable "app_algorithm" {
  description = "Algorithm for JWT tokens"
  type        = string
  sensitive   = true
}

variable "app_access_token_expire_minutes" {
  description = "Access token expiration in minutes"
  type        = string
}

variable "app_version" {
  description = "Application version"
  type        = string
}

variable "app_debug" {
  description = "Enable debug mode"
  type        = string
  default     = "false"
}

variable "app_log_level" {
  description = "Application log level"
  type        = string
  default     = "INFO"
}

variable "app_rate_limit_calls" {
  description = "Rate limit calls per period"
  type        = string
}

variable "app_rate_limit_period" {
  description = "Rate limit period"
  type        = string
}

variable "app_otp_expiry_minutes" {
  description = "OTP expiry time in minutes"
  type        = string
}

variable "app_aws_access_key_id" {
  description = "AWS access key ID"
  type        = string
  sensitive   = true
}

variable "app_aws_secret_access_key" {
  description = "AWS secret access key"
  type        = string
  sensitive   = true
}

variable "app_upstash_redis_url" {
  description = "Upstash Redis URL"
  type        = string
  sensitive   = true
}

variable "app_upstash_redis_token" {
  description = "Upstash Redis token"
  type        = string
  sensitive   = true
}

variable "app_redis_user_cache_ttl" {
  description = "Redis user cache TTL"
  type        = string
}

variable "app_redis_blacklist_ttl" {
  description = "Redis blacklist TTL"
  type        = string
}

variable "app_aws_ses_from_email" {
  description = "AWS SES from email"
  type        = string
}

variable "app_aws_ses_region" {
  description = "AWS SES region"
  type        = string
}

# Network Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["ap-south-1a", "ap-south-1b"]
}

# Tags
variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}