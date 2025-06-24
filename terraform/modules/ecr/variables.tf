# ============================================================================
# ECR MODULE VARIABLES
# ============================================================================

variable "repository_name" {
  description = "Name of the ECR repository"
  type        = string
}

variable "image_tag_mutability" {
  description = "Whether image tags can be overwritten (MUTABLE) or not (IMMUTABLE)"
  type        = string
  default     = "MUTABLE"
  validation {
    condition     = contains(["MUTABLE", "IMMUTABLE"], var.image_tag_mutability)
    error_message = "Image tag mutability must be either MUTABLE or IMMUTABLE."
  }
}

# Basic Scanning Configuration
variable "scan_on_push" {
  description = "Whether to scan images on push for vulnerabilities"
  type        = bool
  default     = true
}

# Enhanced Scanning Configuration
variable "enable_enhanced_scanning" {
  description = "Whether to enable enhanced scanning with Inspector"
  type        = bool
  default     = false
}

variable "enhanced_scan_frequency" {
  description = "Frequency for enhanced scanning (SCAN_ON_PUSH, CONTINUOUS_SCAN, MANUAL)"
  type        = string
  default     = "SCAN_ON_PUSH"
  validation {
    condition     = contains(["SCAN_ON_PUSH", "CONTINUOUS_SCAN", "MANUAL"], var.enhanced_scan_frequency)
    error_message = "Enhanced scan frequency must be one of: SCAN_ON_PUSH, CONTINUOUS_SCAN, MANUAL."
  }
}

# Encryption Configuration
variable "encryption_type" {
  description = "Encryption type for the repository (AES256 or KMS)"
  type        = string
  default     = "AES256"
  validation {
    condition     = contains(["AES256", "KMS"], var.encryption_type)
    error_message = "Encryption type must be either AES256 or KMS."
  }
}

variable "kms_key_id" {
  description = "KMS key ID for repository encryption (only used when encryption_type is KMS)"
  type        = string
  default     = ""
}

# Lifecycle Policy Configuration
variable "enable_lifecycle_policy" {
  description = "Whether to enable a lifecycle policy to manage old images"
  type        = bool
  default     = true
}

variable "max_image_count" {
  description = "Maximum number of tagged images to keep in the repository"
  type        = number
  default     = 10
}

variable "untagged_image_days" {
  description = "Number of days to keep untagged images"
  type        = number
  default     = 1
}

variable "keep_image_tag_prefixes" {
  description = "List of image tag prefixes to keep in lifecycle policy"
  type        = list(string)
  default     = ["latest", "v", "release"]
}

# Repository Policy
variable "repository_policy" {
  description = "JSON repository policy for cross-account access"
  type        = string
  default     = ""
}

# Cross-Region Replication
variable "enable_cross_region_replication" {
  description = "Whether to enable cross-region replication"
  type        = bool
  default     = false
}

variable "replication_destination_region" {
  description = "Destination region for replication"
  type        = string
  default     = "us-east-1"
}

variable "replication_destination_registry_id" {
  description = "Destination registry ID for replication (current account if empty)"
  type        = string
  default     = ""
}

# Tags
variable "tags" {
  description = "Tags to apply to the ECR repository"
  type        = map(string)
  default     = {}
}