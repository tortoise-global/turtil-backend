# ============================================================================
# EC2 MODULE VARIABLES
# ============================================================================

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "ami_id" {
  description = "AMI ID for the instance"
  type        = string
}

variable "instance_type" {
  description = "Instance type"
  type        = string
  default     = "t3.micro"
}

variable "key_name" {
  description = "Name of the EC2 key pair"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID where the instance will be launched"
  type        = string
}

variable "security_group_ids" {
  description = "List of security group IDs"
  type        = list(string)
}

variable "iam_instance_profile_name" {
  description = "Name of the IAM instance profile"
  type        = string
  default     = null
}

variable "user_data_script" {
  description = "Path to user data script template"
  type        = string
  default     = null
}

variable "user_data_vars" {
  description = "Variables to pass to user data script"
  type        = map(string)
  default     = {}
}

variable "root_volume_type" {
  description = "Type of root volume"
  type        = string
  default     = "gp3"
}

variable "root_volume_size" {
  description = "Size of root volume in GB"
  type        = number
  default     = 20
}

variable "root_volume_encrypted" {
  description = "Enable encryption for root volume"
  type        = bool
  default     = true
}

variable "additional_volumes" {
  description = "List of additional EBS volumes"
  type = list(object({
    name        = string
    device_name = string
    volume_type = string
    volume_size = number
    encrypted   = bool
  }))
  default = []
}

variable "metadata_http_endpoint" {
  description = "Whether the metadata service is available"
  type        = string
  default     = "enabled"
}

variable "metadata_http_tokens" {
  description = "Whether the metadata service requires session tokens"
  type        = string
  default     = "required"
}

variable "metadata_http_put_response_hop_limit" {
  description = "Desired HTTP PUT response hop limit for instance metadata requests"
  type        = number
  default     = 1
}

variable "instance_metadata_tags" {
  description = "Enables or disables access to instance tags from the instance metadata service"
  type        = string
  default     = "disabled"
}

variable "detailed_monitoring" {
  description = "Enable detailed monitoring"
  type        = bool
  default     = false
}

variable "availability_zone" {
  description = "Availability zone for the instance"
  type        = string
  default     = null
}

variable "tenancy" {
  description = "Tenancy of the instance"
  type        = string
  default     = "default"
}

variable "cpu_credits" {
  description = "Credit option for CPU usage (burstable instances only)"
  type        = string
  default     = "standard"
}

variable "associate_elastic_ip" {
  description = "Associate an Elastic IP with the instance"
  type        = bool
  default     = false
}

variable "enable_cloudwatch_alarms" {
  description = "Enable CloudWatch alarms for the instance"
  type        = bool
  default     = false
}

variable "cpu_alarm_threshold" {
  description = "CPU utilization threshold for alarm"
  type        = number
  default     = 80
}

variable "alarm_actions" {
  description = "List of alarm actions (SNS topic ARNs)"
  type        = list(string)
  default     = []
}

variable "additional_tags" {
  description = "Additional tags for the instance"
  type        = map(string)
  default     = {}
}