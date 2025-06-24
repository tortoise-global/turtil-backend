# ============================================================================
# DATABASE MODULE - MULTI-ENVIRONMENT SUPPORT
# ============================================================================
# Supports both RDS PostgreSQL (dev/test) and Aurora Serverless v2 (prod)

locals {
  db_identifier = "${var.project_name}-${var.environment}"
  is_aurora = var.database_type == "aurora-serverless-v2"
  is_production = var.environment == "prod"
}

# KMS Key for database encryption
resource "aws_kms_key" "database" {
  count = var.enable_backup_encryption ? 1 : 0
  
  description             = "KMS key for ${local.db_identifier} database encryption"
  deletion_window_in_days = var.environment == "prod" ? 30 : 7
  enable_key_rotation     = var.environment == "prod"

  tags = merge(var.tags, {
    Name = "${local.db_identifier}-db-key"
    Purpose = "database-encryption"
  })
}

resource "aws_kms_alias" "database" {
  count = var.enable_backup_encryption ? 1 : 0
  
  name          = "alias/${local.db_identifier}-db"
  target_key_id = aws_kms_key.database[0].key_id
}

# DB Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "${local.db_identifier}-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = merge(var.tags, {
    Name = "${local.db_identifier}-subnet-group"
  })
}

# Security Group for Database
resource "aws_security_group" "database" {
  name_prefix = "${local.db_identifier}-db-"
  vpc_id      = var.vpc_id
  description = "Security group for ${local.db_identifier} database"

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.app_security_group_id]
    description     = "PostgreSQL access from application servers"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = merge(var.tags, {
    Name = "${local.db_identifier}-db-sg"
  })
  
  lifecycle {
    create_before_destroy = true
  }
}

# Random password for database
resource "random_password" "database" {
  length  = 16
  special = true
}

# ============================================================================
# AURORA SERVERLESS V2 CLUSTER (Production)
# ============================================================================

resource "aws_rds_cluster" "aurora" {
  count = local.is_aurora ? 1 : 0

  cluster_identifier      = "${local.db_identifier}-aurora"
  engine                 = "aurora-postgresql"
  engine_mode            = "provisioned"
  engine_version         = var.postgres_version
  database_name          = var.database_name
  master_username        = var.database_username
  master_password        = random_password.database.result
  
  # Serverless v2 scaling configuration
  serverlessv2_scaling_configuration {
    max_capacity = var.aurora_max_capacity
    min_capacity = var.aurora_min_capacity
  }

  # Network and Security
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.database.id]
  port                   = 5432

  # Backup Configuration
  backup_retention_period = var.database_backup_retention
  backup_window          = var.backup_window
  maintenance_window     = var.maintenance_window
  copy_tags_to_snapshot  = true

  # Encryption
  storage_encrypted = var.enable_aurora_encryption
  kms_key_id       = var.enable_backup_encryption ? aws_kms_key.database[0].arn : null

  # Performance and Monitoring
  enabled_cloudwatch_logs_exports = ["postgresql"]
  performance_insights_enabled    = var.enable_performance_insights
  performance_insights_retention_period = var.enable_performance_insights ? 7 : null

  # Backtrack (if supported by version)
  backtrack_window = var.enable_aurora_backtrack ? var.aurora_backtrack_window : 0

  # Production Safety
  deletion_protection  = var.enable_deletion_protection
  skip_final_snapshot = !var.enable_deletion_protection
  final_snapshot_identifier = var.enable_deletion_protection ? "${local.db_identifier}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}" : null

  # Enhanced Monitoring
  db_cluster_parameter_group_name = aws_rds_cluster_parameter_group.aurora[0].name

  tags = merge(var.tags, {
    Name = "${local.db_identifier}-aurora-cluster"
    DatabaseType = "aurora-serverless-v2"
  })

  depends_on = [aws_cloudwatch_log_group.postgresql]
}

# Aurora Cluster Instance
resource "aws_rds_cluster_instance" "aurora" {
  count = local.is_aurora ? 1 : 0

  identifier           = "${local.db_identifier}-aurora-instance"
  cluster_identifier   = aws_rds_cluster.aurora[0].id
  instance_class       = "db.serverless"
  engine              = aws_rds_cluster.aurora[0].engine
  engine_version      = aws_rds_cluster.aurora[0].engine_version
  
  performance_insights_enabled = var.enable_performance_insights
  monitoring_interval = var.enable_detailed_monitoring ? 60 : 0
  monitoring_role_arn = var.enable_detailed_monitoring ? aws_iam_role.enhanced_monitoring[0].arn : null

  tags = merge(var.tags, {
    Name = "${local.db_identifier}-aurora-instance"
  })
}

# Aurora Parameter Group
resource "aws_rds_cluster_parameter_group" "aurora" {
  count = local.is_aurora ? 1 : 0

  family = "aurora-postgresql15"
  name   = "${local.db_identifier}-aurora-params"

  parameter {
    name  = "log_statement"
    value = var.environment == "prod" ? "ddl" : "all"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = var.environment == "prod" ? "1000" : "100"
  }

  tags = var.tags
}

# ============================================================================
# RDS POSTGRESQL INSTANCE (Development/Testing)
# ============================================================================

resource "aws_db_instance" "postgres" {
  count = local.is_aurora ? 0 : 1

  identifier = "${local.db_identifier}-postgres"
  
  # Engine Configuration
  engine               = "postgres"
  engine_version       = var.postgres_version
  instance_class       = var.database_instance_class
  allocated_storage    = var.database_allocated_storage
  max_allocated_storage = var.database_allocated_storage * 2
  storage_type         = "gp3"
  storage_encrypted    = var.enable_backup_encryption
  kms_key_id          = var.enable_backup_encryption ? aws_kms_key.database[0].arn : null

  # Database Configuration
  db_name  = var.database_name
  username = var.database_username
  password = random_password.database.result
  port     = 5432

  # Network and Security
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.database.id]
  publicly_accessible    = false

  # Backup Configuration
  backup_retention_period = var.database_backup_retention
  backup_window          = var.backup_window
  maintenance_window     = var.maintenance_window
  copy_tags_to_snapshot  = true

  # High Availability
  multi_az = var.database_multi_az

  # Monitoring
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  performance_insights_enabled    = var.enable_performance_insights
  performance_insights_retention_period = var.enable_performance_insights ? 7 : null
  monitoring_interval = var.enable_detailed_monitoring ? 60 : 0
  monitoring_role_arn = var.enable_detailed_monitoring ? aws_iam_role.enhanced_monitoring[0].arn : null

  # Parameter Group
  parameter_group_name = aws_db_parameter_group.postgres[0].name

  # Safety
  deletion_protection = var.enable_deletion_protection
  skip_final_snapshot = !var.enable_deletion_protection
  final_snapshot_identifier = var.enable_deletion_protection ? "${local.db_identifier}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}" : null

  # Auto Upgrade
  auto_minor_version_upgrade = var.environment != "prod"
  allow_major_version_upgrade = false

  tags = merge(var.tags, {
    Name = "${local.db_identifier}-postgres"
    DatabaseType = "rds-postgresql"
  })

  depends_on = [aws_cloudwatch_log_group.postgresql]
}

# RDS Parameter Group
resource "aws_db_parameter_group" "postgres" {
  count = local.is_aurora ? 0 : 1

  family = "postgres15"
  name   = "${local.db_identifier}-postgres-params"

  parameter {
    name  = "log_statement"
    value = var.environment == "prod" ? "ddl" : "all"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = var.environment == "prod" ? "1000" : "100"
  }

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements"
  }

  tags = var.tags
}

# ============================================================================
# MONITORING AND LOGGING
# ============================================================================

# CloudWatch Log Group for PostgreSQL logs
resource "aws_cloudwatch_log_group" "postgresql" {
  name              = "/aws/rds/instance/${local.db_identifier}/postgresql"
  retention_in_days = var.cloudwatch_log_retention
  kms_key_id       = var.enable_backup_encryption ? aws_kms_key.database[0].arn : null

  tags = merge(var.tags, {
    Name = "${local.db_identifier}-postgresql-logs"
  })
}

# IAM Role for Enhanced Monitoring
resource "aws_iam_role" "enhanced_monitoring" {
  count = var.enable_detailed_monitoring ? 1 : 0

  name = "${local.db_identifier}-enhanced-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "enhanced_monitoring" {
  count = var.enable_detailed_monitoring ? 1 : 0

  role       = aws_iam_role.enhanced_monitoring[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# ============================================================================
# SECRETS MANAGER (Optional)
# ============================================================================

resource "aws_secretsmanager_secret" "database" {
  count = var.enable_secrets_manager ? 1 : 0

  name                    = "${local.db_identifier}-database-credentials"
  description             = "Database credentials for ${local.db_identifier}"
  recovery_window_in_days = var.environment == "prod" ? 30 : 0

  tags = merge(var.tags, {
    Name = "${local.db_identifier}-db-secret"
  })
}

resource "aws_secretsmanager_secret_version" "database" {
  count = var.enable_secrets_manager ? 1 : 0

  secret_id = aws_secretsmanager_secret.database[0].id
  secret_string = jsonencode({
    username = var.database_username
    password = random_password.database.result
    engine   = "postgres"
    host     = local.is_aurora ? aws_rds_cluster.aurora[0].endpoint : aws_db_instance.postgres[0].endpoint
    port     = 5432
    dbname   = var.database_name
  })
}