# Outputs for Turtil Backend Terraform configuration

output "s3_bucket_name" {
  description = "Name of the created S3 bucket"
  value       = aws_s3_bucket.turtil_uploads.bucket
}

output "s3_bucket_arn" {
  description = "ARN of the created S3 bucket"
  value       = aws_s3_bucket.turtil_uploads.arn
}

output "s3_bucket_domain_name" {
  description = "Domain name of the S3 bucket"
  value       = aws_s3_bucket.turtil_uploads.bucket_domain_name
}

output "s3_bucket_regional_domain_name" {
  description = "Regional domain name of the S3 bucket"
  value       = aws_s3_bucket.turtil_uploads.bucket_regional_domain_name
}

# IAM outputs removed - use your existing AWS credentials

output "aws_region" {
  description = "AWS region where resources are created"
  value       = data.aws_region.current.name
}

# Environment variables for your .env file
output "env_variables" {
  description = "Environment variables to add to your .env file"
  value = {
    AWS_REGION     = data.aws_region.current.name
    S3_BUCKET_NAME = aws_s3_bucket.turtil_uploads.bucket
  }
  sensitive = false
}