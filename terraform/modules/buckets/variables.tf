# ============================================================================
# S3 BUCKET MODULE VARIABLES
# ============================================================================

variable "bucket_name" {
  description = "The name of the S3 bucket"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, test, prod)"
  type        = string
}

variable "bucket_purpose" {
  description = "Purpose of the bucket (app-storage, uploads, logs, etc.)"
  type        = string
  default     = "app-storage"
}

variable "force_destroy" {
  description = "Enable force destroy to delete all objects when bucket is destroyed"
  type        = bool
  default     = false
}

# Versioning Configuration
variable "enable_versioning" {
  description = "Whether to enable S3 versioning"
  type        = bool
  default     = true
}

# Encryption Configuration
variable "kms_key_id" {
  description = "KMS key ID for bucket encryption (leave empty for AES256)"
  type        = string
  default     = ""
}

# Access Control
variable "block_public_access" {
  description = "Whether to block all public access to the bucket"
  type        = bool
  default     = true
}

# CORS Configuration
variable "enable_cors" {
  description = "Whether to enable CORS configuration"
  type        = bool
  default     = false
}

variable "cors_allowed_headers" {
  description = "List of allowed headers for CORS"
  type        = list(string)
  default     = ["*"]
}

variable "cors_allowed_methods" {
  description = "List of allowed methods for CORS"
  type        = list(string)
  default     = ["PUT", "POST", "GET"]
}

variable "cors_allowed_origins" {
  description = "List of allowed origins for CORS"
  type        = list(string)
  default     = ["*"]
}

variable "cors_expose_headers" {
  description = "List of headers to expose in CORS"
  type        = list(string)
  default     = ["ETag"]
}

variable "cors_max_age_seconds" {
  description = "Maximum age in seconds for CORS preflight requests"
  type        = number
  default     = 3000
}

# Lifecycle Configuration
variable "enable_lifecycle" {
  description = "Whether to enable lifecycle policies"
  type        = bool
  default     = true
}

variable "transition_to_ia_days" {
  description = "Number of days after which to transition to Infrequent Access"
  type        = number
  default     = 30
}

variable "transition_to_glacier_days" {
  description = "Number of days after which to transition to Glacier"
  type        = number
  default     = 90
}

variable "transition_to_deep_archive_days" {
  description = "Number of days after which to transition to Deep Archive"
  type        = number
  default     = 365
}

variable "expiration_days" {
  description = "Number of days after which to expire objects (0 to disable)"
  type        = number
  default     = 0
}

# Intelligent Tiering
variable "enable_intelligent_tiering" {
  description = "Whether to enable S3 Intelligent Tiering"
  type        = bool
  default     = false
}

variable "intelligent_tiering_archive_days" {
  description = "Days after which to archive in Intelligent Tiering"
  type        = number
  default     = 90
}

variable "intelligent_tiering_deep_archive_days" {
  description = "Days after which to deep archive in Intelligent Tiering"
  type        = number
  default     = 180
}

# Cross-Region Replication
variable "enable_cross_region_replication" {
  description = "Whether to enable cross-region replication"
  type        = bool
  default     = false
}

variable "replication_destination_bucket" {
  description = "Destination bucket ARN for cross-region replication"
  type        = string
  default     = ""
}

variable "replication_storage_class" {
  description = "Storage class for replicated objects"
  type        = string
  default     = "STANDARD_IA"
}

variable "replication_kms_key_id" {
  description = "KMS key ID for replication encryption"
  type        = string
  default     = ""
}

# Notifications
variable "enable_notifications" {
  description = "Whether to enable bucket notifications"
  type        = bool
  default     = false
}

variable "enable_eventbridge_notifications" {
  description = "Whether to enable EventBridge notifications"
  type        = bool
  default     = false
}

# Logging (Legacy variable for backward compatibility)
variable "enable_cloudwatch_logging" {
  description = "Enable or disable CloudWatch logging for the S3 bucket (deprecated)"
  type        = bool
  default     = false
}

# Tags
variable "tags" {
  description = "A map of tags to assign to the S3 bucket"
  type        = map(string)
  default     = {}
}

