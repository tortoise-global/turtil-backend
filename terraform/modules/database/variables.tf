# ============================================================================
# DATABASE MODULE VARIABLES
# ============================================================================

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, test, prod)"
  type        = string
}

variable "database_type" {
  description = "Database type (rds or aurora-serverless-v2)"
  type        = string
  default     = "rds"
  validation {
    condition     = contains(["rds", "aurora-serverless-v2"], var.database_type)
    error_message = "Database type must be either 'rds' or 'aurora-serverless-v2'."
  }
}

# Database Configuration
variable "database_name" {
  description = "Name of the database"
  type        = string
}

variable "database_username" {
  description = "Username for the database"
  type        = string
  default     = "postgres"
}

variable "postgres_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "15.4"
}

# RDS Configuration
variable "database_instance_class" {
  description = "Database instance class for RDS"
  type        = string
  default     = "db.t4g.micro"
}

variable "database_allocated_storage" {
  description = "Allocated storage for RDS instance (GB)"
  type        = number
  default     = 20
}

variable "database_multi_az" {
  description = "Whether to enable Multi-AZ deployment"
  type        = bool
  default     = false
}

# Aurora Serverless v2 Configuration
variable "aurora_min_capacity" {
  description = "Minimum Aurora Serverless v2 capacity (ACU)"
  type        = number
  default     = 0.5
}

variable "aurora_max_capacity" {
  description = "Maximum Aurora Serverless v2 capacity (ACU)"
  type        = number
  default     = 16
}

variable "enable_aurora_backtrack" {
  description = "Whether to enable Aurora Backtrack"
  type        = bool
  default     = false
}

variable "aurora_backtrack_window" {
  description = "Aurora Backtrack window in hours"
  type        = number
  default     = 24
}

# Backup Configuration
variable "database_backup_retention" {
  description = "Number of days to retain database backups"
  type        = number
  default     = 7
}

variable "backup_window" {
  description = "Preferred backup window"
  type        = string
  default     = "03:00-04:00"
}

variable "maintenance_window" {
  description = "Preferred maintenance window"
  type        = string
  default     = "sun:04:00-sun:05:00"
}

# Security Configuration
variable "enable_deletion_protection" {
  description = "Whether to enable deletion protection"
  type        = bool
  default     = false
}

variable "enable_backup_encryption" {
  description = "Whether to enable backup encryption"
  type        = bool
  default     = true
}

variable "enable_aurora_encryption" {
  description = "Whether to enable Aurora encryption at rest"
  type        = bool
  default     = true
}

variable "enable_secrets_manager" {
  description = "Whether to store credentials in Secrets Manager"
  type        = bool
  default     = false
}

# Monitoring Configuration
variable "enable_performance_insights" {
  description = "Whether to enable Performance Insights"
  type        = bool
  default     = false
}

variable "enable_detailed_monitoring" {
  description = "Whether to enable detailed CloudWatch monitoring"
  type        = bool
  default     = false
}

variable "cloudwatch_log_retention" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 14
}

# Network Configuration
variable "vpc_id" {
  description = "VPC ID where the database will be created"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for the database"
  type        = list(string)
}

variable "app_security_group_id" {
  description = "Security group ID of the application servers"
  type        = string
}

# Tags
variable "tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}