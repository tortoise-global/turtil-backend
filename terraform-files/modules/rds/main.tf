# RDS Module with Destroy Protection

# Random password for database
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# DB Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "turtil-backend-${var.environment}-db-subnet-group"
  subnet_ids = var.subnet_ids

  tags = merge(var.tags, {
    Name = "turtil-backend-${var.environment}-db-subnet-group"
  })
}

# RDS Instance with Destroy Protection
resource "aws_db_instance" "main" {
  identifier = "turtil-backend-${var.environment}-rds"

  # Database Configuration
  engine         = "postgres"
  engine_version = "17.5"
  instance_class = var.instance_class

  # Storage Configuration
  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp3"
  storage_encrypted     = true

  # Database Settings
  db_name  = replace(var.database_name, "-", "_") # PostgreSQL doesn't allow hyphens
  username = "turtil_admin"
  password = random_password.db_password.result

  # Network Configuration
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [var.vpc_security_group_id]
  publicly_accessible    = var.environment == "dev" ? true : false

  # Backup Configuration
  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"

  # Monitoring
  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_monitoring.arn

  # Performance Insights
  performance_insights_enabled          = true
  performance_insights_retention_period = 7

  # Security
  deletion_protection       = true # CRITICAL: Prevent accidental deletion
  skip_final_snapshot       = false
  final_snapshot_identifier = "turtil-backend-${var.environment}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"

  # Enable automated minor version upgrades
  auto_minor_version_upgrade = true

  # Apply changes immediately (dev environment only)
  apply_immediately = var.environment == "dev" ? true : false

  tags = merge(var.tags, {
    Name              = "turtil-backend-${var.environment}-rds"
    Environment       = var.environment
    DestroyProtection = "true"
  })

  lifecycle {
    prevent_destroy = true # Extra protection at Terraform level
  }
}

# IAM Role for RDS Enhanced Monitoring
resource "aws_iam_role" "rds_monitoring" {
  name = "turtil-backend-${var.environment}-rds-monitoring-role"

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

  tags = merge(var.tags, {
    Name = "turtil-backend-${var.environment}-rds-monitoring-role"
  })
}

# Attach policy to RDS monitoring role
resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# Store database credentials in AWS Secrets Manager
resource "aws_secretsmanager_secret" "db_credentials" {
  name        = "turtil-backend-${var.environment}-db-credentials"
  description = "Database credentials for turtil-backend ${var.environment}"

  tags = merge(var.tags, {
    Name = "turtil-backend-${var.environment}-db-credentials"
  })
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username     = aws_db_instance.main.username
    password     = random_password.db_password.result
    endpoint     = aws_db_instance.main.endpoint
    port         = aws_db_instance.main.port
    dbname       = aws_db_instance.main.db_name
    database_url = "postgresql+asyncpg://${aws_db_instance.main.username}:${random_password.db_password.result}@${aws_db_instance.main.endpoint}:${aws_db_instance.main.port}/${aws_db_instance.main.db_name}"
  })
}
