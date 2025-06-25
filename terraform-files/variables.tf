# Core AWS Configuration
variable "aws_region" {
  description = "AWS region for infrastructure"
  type        = string
  default     = "ap-south-2"
}

# User-provided secrets (from GitHub Secrets)
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
  default     = "support@turtil.co"
}