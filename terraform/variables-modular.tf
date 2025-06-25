# ============================================================================
# MODULAR TERRAFORM VARIABLES
# ============================================================================

# Project Configuration
variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "turtil-backend-dev"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"
}

variable "app_environment" {
  description = "Application environment"
  type        = string
  default     = "dev"
}

# Security & Authentication
variable "app_secret_key" {
  description = "JWT secret key"
  type        = string
  sensitive   = true
}

variable "app_algorithm" {
  description = "JWT algorithm"
  type        = string
  default     = "HS256"
}

variable "app_access_token_expire_minutes" {
  description = "Access token expiry in minutes"
  type        = number
  default     = 30
}

variable "app_refresh_token_expire_minutes" {
  description = "Refresh token expiry in minutes"
  type        = number
  default     = 43200
}

# OTP Configuration
variable "app_otp_expiry_minutes" {
  description = "OTP expiry in minutes"
  type        = number
  default     = 5
}

variable "app_otp_max_attempts" {
  description = "Maximum OTP attempts"
  type        = number
  default     = 3
}

variable "app_dev_otp" {
  description = "Development OTP code"
  type        = string
  default     = "123456"
}

# Application Settings
variable "app_cors_origins" {
  description = "CORS allowed origins"
  type        = string
  default     = "http://localhost:3000,http://127.0.0.1:3000"
}

variable "app_allowed_hosts" {
  description = "Allowed hosts"
  type        = string
  default     = "localhost,127.0.0.1"
}

variable "app_rate_limit_calls" {
  description = "Rate limit calls per period"
  type        = number
  default     = 100
}

variable "app_rate_limit_period" {
  description = "Rate limit period in seconds"
  type        = number
  default     = 60
}

# Redis Configuration
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
  description = "Redis user cache TTL in seconds"
  type        = number
  default     = 300
}

variable "app_redis_blacklist_ttl" {
  description = "Redis blacklist TTL in seconds"
  type        = number
  default     = 1800
}

# Database Configuration
variable "app_db_username" {
  description = "Database master username"
  type        = string
  default     = "turtiluser"
}

variable "app_db_password" {
  description = "Database master password"
  type        = string
  sensitive   = true
}

# AWS Services
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

variable "app_aws_ses_from_email" {
  description = "AWS SES from email"
  type        = string
  default     = "noreply@turtil.co"
}

# Infrastructure Configuration
variable "custom_ami_id" {
  description = "Custom AMI ID with Docker pre-installed"
  type        = string
  default     = "ami-0eb4445f6c0a650a1"  # Fallback to Ubuntu 24.04 LTS ARM64
}