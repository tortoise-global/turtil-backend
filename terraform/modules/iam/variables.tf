# ============================================================================
# IAM MODULE VARIABLES
# ============================================================================

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN of the S3 bucket for access policy"
  type        = string
  default     = null
}

variable "enable_ses_access" {
  description = "Enable SES access for the role"
  type        = bool
  default     = false
}

variable "enable_cloudwatch_logs" {
  description = "Enable CloudWatch Logs access for the role"
  type        = bool
  default     = false
}

variable "custom_policies" {
  description = "List of custom IAM policies to attach to the role"
  type        = list(string)
  default     = []
}