variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for the RDS cluster"
  type        = string
}
variable "aurora_postgres_name" {
  description = "Name for aurora"
  type         =  string
}
variable "allowed_cidr_blocks" {
  description = "Allowed inbound CIDR blocks"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "db_name" {
  description = "Initial DB name"
  type        = string
}

variable "db_username" {
  description = "Aurora master username"
  type        = string
}

variable "db_password" {
  description = "Aurora master password"
  type        = string
  sensitive   = true
}

variable "engine_version" {
  description = "Aurora engine version"
  type        = string
  default     = "16.2"
}

variable "serverless_min_capacity" {
  description = "Serverless min capacity (ACUs)"
  type        = number
  default     = 0.5
}

variable "serverless_max_capacity" {
  description = "Serverless max capacity (ACUs)"
  type        = number
  default     = 3.0
}

variable "publicly_accessible" {
  description = "Make instance publicly accessible"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
