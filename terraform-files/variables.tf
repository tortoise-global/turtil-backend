variable "ecr_account_id" {
  description = "AWS Account ID for ECR registry"
  type        = string
  sensitive   = true
}

variable "ecr_repository_name" {
  description = "ECR repository name for different environments"
  type        = string
}

variable "ecr_env_tags" {
  type = map(string)
  default = {
    "dev"  = "dev"
    "test" = "test"
    "prod" = "prod"
  }
}
