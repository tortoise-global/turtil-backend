# ============================================================================
# DATABASE MODULE OUTPUTS
# ============================================================================

# Database Connection Information
output "database_endpoint" {
  description = "Database endpoint for application connections"
  value       = local.is_aurora ? aws_rds_cluster.aurora[0].endpoint : aws_db_instance.postgres[0].endpoint
  sensitive   = false
}

output "database_reader_endpoint" {
  description = "Database reader endpoint (Aurora only)"
  value       = local.is_aurora ? aws_rds_cluster.aurora[0].reader_endpoint : null
  sensitive   = false
}

output "database_port" {
  description = "Database port"
  value       = 5432
  sensitive   = false
}

output "database_name" {
  description = "Database name"
  value       = var.database_name
  sensitive   = false
}

output "database_username" {
  description = "Database username"
  value       = var.database_username
  sensitive   = true
}

output "database_password" {
  description = "Database password"
  value       = random_password.database.result
  sensitive   = true
}

# Connection String
output "database_url" {
  description = "Full database connection URL"
  value       = "postgresql://${var.database_username}:${random_password.database.result}@${local.is_aurora ? aws_rds_cluster.aurora[0].endpoint : aws_db_instance.postgres[0].endpoint}:5432/${var.database_name}"
  sensitive   = true
}

output "database_url_asyncpg" {
  description = "Database connection URL for asyncpg (Python)"
  value       = "postgresql+asyncpg://${var.database_username}:${random_password.database.result}@${local.is_aurora ? aws_rds_cluster.aurora[0].endpoint : aws_db_instance.postgres[0].endpoint}:5432/${var.database_name}"
  sensitive   = true
}

# Resource Identifiers
output "database_identifier" {
  description = "Database instance/cluster identifier"
  value       = local.is_aurora ? aws_rds_cluster.aurora[0].cluster_identifier : aws_db_instance.postgres[0].identifier
  sensitive   = false
}

output "database_arn" {
  description = "Database ARN"
  value       = local.is_aurora ? aws_rds_cluster.aurora[0].arn : aws_db_instance.postgres[0].arn
  sensitive   = false
}

output "database_resource_id" {
  description = "Database resource ID"
  value       = local.is_aurora ? aws_rds_cluster.aurora[0].cluster_resource_id : aws_db_instance.postgres[0].resource_id
  sensitive   = false
}

# Security
output "database_security_group_id" {
  description = "Security group ID for the database"
  value       = aws_security_group.database.id
  sensitive   = false
}

output "database_subnet_group_name" {
  description = "Database subnet group name"
  value       = aws_db_subnet_group.main.name
  sensitive   = false
}

# Encryption
output "database_kms_key_id" {
  description = "KMS key ID used for database encryption"
  value       = var.enable_backup_encryption ? aws_kms_key.database[0].key_id : null
  sensitive   = false
}

output "database_kms_key_arn" {
  description = "KMS key ARN used for database encryption"
  value       = var.enable_backup_encryption ? aws_kms_key.database[0].arn : null
  sensitive   = false
}

# Secrets Manager
output "secrets_manager_secret_arn" {
  description = "Secrets Manager secret ARN for database credentials"
  value       = var.enable_secrets_manager ? aws_secretsmanager_secret.database[0].arn : null
  sensitive   = false
}

# Monitoring
output "cloudwatch_log_group_name" {
  description = "CloudWatch log group name for database logs"
  value       = aws_cloudwatch_log_group.postgresql.name
  sensitive   = false
}

# Database Type and Configuration
output "database_type" {
  description = "Type of database (rds or aurora-serverless-v2)"
  value       = var.database_type
  sensitive   = false
}

output "database_engine" {
  description = "Database engine"
  value       = local.is_aurora ? aws_rds_cluster.aurora[0].engine : aws_db_instance.postgres[0].engine
  sensitive   = false
}

output "database_engine_version" {
  description = "Database engine version"
  value       = local.is_aurora ? aws_rds_cluster.aurora[0].engine_version : aws_db_instance.postgres[0].engine_version
  sensitive   = false
}

# Aurora Specific Outputs
output "aurora_cluster_members" {
  description = "List of Aurora cluster members"
  value       = local.is_aurora ? aws_rds_cluster.aurora[0].cluster_members : []
  sensitive   = false
}

output "aurora_availability_zones" {
  description = "List of availability zones for Aurora cluster"
  value       = local.is_aurora ? aws_rds_cluster.aurora[0].availability_zones : []
  sensitive   = false
}

# Backup Information
output "backup_retention_period" {
  description = "Backup retention period in days"
  value       = var.database_backup_retention
  sensitive   = false
}

output "backup_window" {
  description = "Preferred backup window"
  value       = var.backup_window
  sensitive   = false
}

output "maintenance_window" {
  description = "Preferred maintenance window"
  value       = var.maintenance_window
  sensitive   = false
}