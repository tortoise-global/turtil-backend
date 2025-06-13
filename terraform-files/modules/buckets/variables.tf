variable "bucket_name" {
  description = "The name of the S3 bucket"
  type        = string
}

variable "force_destroy" {
  description = "Enable force destroy to delete all objects when bucket is destroyed"
  type        = bool
  default     = false
}

variable "tags" {
  description = "A map of tags to assign to the S3 bucket"
  type        = map(string)
  default     = {}
}

variable "enable_cloudwatch_logging" {
  description = "Enable or disable CloudWatch logging for the S3 bucket"
  type        = bool
  default     = false
}

