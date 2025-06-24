# ============================================================================
# ECR MODULE OUTPUTS
# ============================================================================

output "repository_url" {
  description = "The URL of the ECR repository"
  value       = aws_ecr_repository.this.repository_url
}

output "repository_arn" {
  description = "The ARN of the ECR repository"
  value       = aws_ecr_repository.this.arn
}

output "repository_name" {
  description = "The name of the ECR repository"
  value       = aws_ecr_repository.this.name
}

output "repository_registry_id" {
  description = "The registry ID where the repository was created"
  value       = aws_ecr_repository.this.registry_id
}

output "repository_uri" {
  description = "The URI of the repository (without tag)"
  value       = aws_ecr_repository.this.repository_url
}

# Configuration Details
output "image_tag_mutability" {
  description = "The tag mutability setting for the repository"
  value       = aws_ecr_repository.this.image_tag_mutability
}

output "encryption_type" {
  description = "The encryption type used for the repository"
  value       = var.encryption_type
}

output "scan_on_push_enabled" {
  description = "Whether scan on push is enabled"
  value       = var.scan_on_push
}

output "enhanced_scanning_enabled" {
  description = "Whether enhanced scanning is enabled"
  value       = var.enable_enhanced_scanning
}

# Lifecycle Policy
output "lifecycle_policy_enabled" {
  description = "Whether lifecycle policy is enabled"
  value       = var.enable_lifecycle_policy
}

output "max_image_count" {
  description = "Maximum number of images to keep"
  value       = var.max_image_count
}

# Cross-Region Replication
output "cross_region_replication_enabled" {
  description = "Whether cross-region replication is enabled"
  value       = var.enable_cross_region_replication
}

# Useful for CI/CD
output "docker_push_command" {
  description = "Docker command to push images to this repository"
  value       = "docker push ${aws_ecr_repository.this.repository_url}:latest"
}

output "docker_login_command" {
  description = "AWS CLI command to authenticate Docker to this ECR registry"
  value       = "aws ecr get-login-password --region ${data.aws_region.current.name} | docker login --username AWS --password-stdin ${aws_ecr_repository.this.registry_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com"
}

# Data sources for outputs
data "aws_region" "current" {}