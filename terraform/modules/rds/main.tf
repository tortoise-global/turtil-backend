# ============================================================================
# RDS MODULE - PostgreSQL Database
# ============================================================================

resource "aws_db_instance" "main" {
  identifier             = "${var.project_name}-${var.environment}"
  engine                 = "postgres"
  engine_version         = var.postgres_version
  instance_class         = var.instance_class
  allocated_storage      = var.allocated_storage
  max_allocated_storage  = var.max_allocated_storage
  
  db_name  = var.database_name
  username = var.username
  password = var.password
  
  publicly_accessible    = var.publicly_accessible
  db_subnet_group_name   = var.db_subnet_group_name
  vpc_security_group_ids = var.security_group_ids
  
  backup_retention_period = var.backup_retention_period
  backup_window          = var.backup_window
  maintenance_window     = var.maintenance_window
  
  skip_final_snapshot = var.skip_final_snapshot
  deletion_protection = var.deletion_protection
  
  # Performance Insights
  performance_insights_enabled = var.performance_insights_enabled
  performance_insights_retention_period = var.performance_insights_enabled ? var.performance_insights_retention_period : null
  
  # Monitoring
  monitoring_interval = var.monitoring_interval
  monitoring_role_arn = var.monitoring_interval > 0 ? var.monitoring_role_arn : null
  
  # Storage encryption
  storage_encrypted = var.storage_encrypted
  kms_key_id       = var.kms_key_id
  
  # Parameter group
  parameter_group_name = var.parameter_group_name
  
  # Multi-AZ deployment
  multi_az = var.multi_az
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-database"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Optional: Custom Parameter Group
resource "aws_db_parameter_group" "main" {
  count = var.create_parameter_group ? 1 : 0
  
  family = "postgres15"
  name   = "${var.project_name}-${var.environment}-postgres-params"
  
  dynamic "parameter" {
    for_each = var.parameters
    content {
      name  = parameter.value.name
      value = parameter.value.value
    }
  }
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-postgres-params"
    Environment = var.environment
    Project     = var.project_name
  }
}