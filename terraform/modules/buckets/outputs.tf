# ============================================================================
# S3 BUCKET MODULE OUTPUTS
# ============================================================================

output "bucket_id" {
  description = "The ID of the S3 bucket"
  value       = aws_s3_bucket.main.id
}

output "bucket_arn" {
  description = "The ARN of the S3 bucket"
  value       = aws_s3_bucket.main.arn
}

output "bucket_name" {
  description = "The name of the S3 bucket"
  value       = aws_s3_bucket.main.bucket
}

output "bucket_domain_name" {
  description = "The bucket domain name"
  value       = aws_s3_bucket.main.bucket_domain_name
}

output "bucket_regional_domain_name" {
  description = "The bucket regional domain name"
  value       = aws_s3_bucket.main.bucket_regional_domain_name
}

output "bucket_hosted_zone_id" {
  description = "The Route 53 Hosted Zone ID for this bucket's region"
  value       = aws_s3_bucket.main.hosted_zone_id
}

output "bucket_region" {
  description = "The AWS region this bucket resides in"
  value       = aws_s3_bucket.main.region
}

# CORS Configuration
output "cors_enabled" {
  description = "Whether CORS is enabled for the bucket"
  value       = var.enable_cors
}

# Versioning
output "versioning_enabled" {
  description = "Whether versioning is enabled for the bucket"
  value       = var.enable_versioning
}

# Encryption
output "encryption_algorithm" {
  description = "The encryption algorithm used"
  value       = var.kms_key_id != "" ? "aws:kms" : "AES256"
}

output "kms_key_id" {
  description = "The KMS key ID used for encryption (if any)"
  value       = var.kms_key_id != "" ? var.kms_key_id : null
}

# Lifecycle
output "lifecycle_enabled" {
  description = "Whether lifecycle policies are enabled"
  value       = var.enable_lifecycle
}

# Intelligent Tiering
output "intelligent_tiering_enabled" {
  description = "Whether intelligent tiering is enabled"
  value       = var.enable_intelligent_tiering
}

# Cross-Region Replication
output "cross_region_replication_enabled" {
  description = "Whether cross-region replication is enabled"
  value       = var.enable_cross_region_replication
}

output "replication_role_arn" {
  description = "The ARN of the replication role (if cross-region replication is enabled)"
  value       = var.enable_cross_region_replication ? aws_iam_role.replication[0].arn : null
}

# Public Access
output "public_access_blocked" {
  description = "Whether public access is blocked for the bucket"
  value       = var.block_public_access
}

# Tags
output "bucket_tags" {
  description = "Tags applied to the bucket"
  value       = aws_s3_bucket.main.tags
}

# Legacy outputs for backward compatibility
output "create_bucket_id" {
  description = "The ID of the S3 bucket (legacy)"
  value       = aws_s3_bucket.main.id
}

output "create_bucket_arn" {
  description = "The ARN of the S3 bucket (legacy)"
  value       = aws_s3_bucket.main.arn
}
