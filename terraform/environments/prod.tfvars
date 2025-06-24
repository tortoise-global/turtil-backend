# ============================================================================
# PROD ENVIRONMENT CONFIGURATION
# ============================================================================
# Production-ready configuration with high availability, security, and monitoring
# Optimized for performance, reliability, and compliance

# Environment Configuration
environment = "prod"
project_name = "turtil-backend"

# Compute Configuration (Production Grade)
instance_type = "t4g.medium"          # ARM Graviton2 with adequate resources
min_size = 1                          # Start with 1 instance, scale as needed
max_size = 3                          # Allow scaling to 3 instances
desired_capacity = 2                  # Start with 2 instances for HA
enable_spot_instances = false         # On-demand only for reliability
enable_load_balancer = true           # Full ALB + CloudFront setup

# Database Configuration (Aurora Serverless v2)
database_type = "aurora-serverless-v2"       # Use Aurora Serverless v2
database_instance_class = "db.serverless"    # Serverless instance class
aurora_min_capacity = 0.5                    # Minimum 0.5 ACU
aurora_max_capacity = 32                     # Maximum 32 ACU for high load
database_backup_retention = 30               # 30-day backup retention
database_multi_az = true                     # Multi-AZ for high availability
enable_deletion_protection = true            # Protect against accidental deletion
database_name = "turtil-backend-prod"

# Aurora Specific Configuration
enable_aurora_global_database = false        # Can be enabled for multi-region
aurora_backup_window = "03:00-04:00"         # Backup during low traffic
aurora_maintenance_window = "sun:04:00-sun:05:00"
enable_aurora_backtrack = true               # Enable point-in-time recovery
aurora_backtrack_window = 72                 # 72-hour backtrack window

# Storage Configuration (Production)
s3_bucket_prefix = "turtil-backend"           # S3 bucket prefix
enable_s3_versioning = true                  # Enable versioning for data protection
s3_lifecycle_enabled = true                  # Intelligent lifecycle management
enable_s3_intelligent_tiering = true         # Cost optimization
enable_s3_cross_region_replication = true    # Disaster recovery
s3_replication_region = "ap-southeast-1"     # Secondary region
s3_transition_to_ia_days = 30                # Infrequent Access after 30 days
s3_transition_to_glacier_days = 90           # Glacier after 90 days
s3_transition_to_deep_archive_days = 365     # Deep Archive after 1 year

# Container Registry Configuration (Production)
ecr_repository_name = "turtil-backend"        # ECR repository name
ecr_image_tag_mutability = "IMMUTABLE"       # Immutable tags for prod
ecr_max_image_count = 20                     # Keep more versions for rollback
enable_ecr_vulnerability_scanning = true     # Enhanced security scanning
enable_ecr_image_signing = true              # Image signing for security

# Monitoring and Logging (Comprehensive)
enable_detailed_monitoring = true            # Full monitoring suite
cloudwatch_log_retention = 90                # 90-day log retention
enable_performance_insights = true           # Database performance monitoring
performance_insights_retention = 31          # 31-day PI retention
enable_enhanced_monitoring = true            # OS-level database monitoring

# Security Configuration (Production Grade)
enable_waf = true                            # Web Application Firewall
ssl_certificate_arn = ""                     # SSL certificate ARN (to be provided)
enable_backup_encryption = true              # Encrypt all backups
enable_aurora_encryption = true              # Encrypt Aurora cluster
kms_key_rotation = true                      # Enable key rotation
enable_secrets_manager = true                # Use Secrets Manager for credentials

# Network Configuration (Production)
vpc_cidr = "10.2.0.0/16"
availability_zones = ["ap-south-1a", "ap-south-1b", "ap-south-1c"]
enable_vpc_flow_logs = true                  # Network monitoring
enable_nat_gateway_ha = true                 # HA NAT gateways
enable_vpc_endpoints = true                  # VPC endpoints for AWS services

# Auto Scaling Configuration (Production)
scale_up_threshold = 60                      # Conservative scaling threshold
scale_down_threshold = 20                    # Aggressive scale down for cost
scale_up_adjustment = 2                      # Add 2 instances for faster response
scale_down_adjustment = -1                   # Remove 1 instance cautiously
scale_up_cooldown = 300                      # 5-minute cooldown
scale_down_cooldown = 600                    # 10-minute cooldown

# Load Balancer Configuration
enable_alb_access_logs = true                # Enable ALB access logging
alb_idle_timeout = 60                        # 60-second idle timeout
enable_connection_draining = true            # Graceful connection draining
connection_draining_timeout = 300            # 5-minute draining

# Application Configuration (Production)
debug_mode = false                           # Disable debug mode
log_level = "INFO"                           # Production logging level
enable_application_insights = true           # Application performance monitoring

# Backup and Disaster Recovery
enable_automated_snapshots = true            # Automated EBS snapshots
snapshot_retention_days = 30                 # Keep snapshots for 30 days
enable_cross_region_backup = true            # Cross-region backup replication
backup_schedule = "cron(0 2 * * ? *)"       # Daily at 2 AM UTC

# Compliance and Governance
enable_aws_config = true                     # Configuration compliance
enable_cloudtrail = true                     # API call auditing
cloudtrail_log_retention = 365               # 1-year CloudTrail retention
enable_cost_anomaly_detection = true         # Cost monitoring
enable_trusted_advisor = true                # AWS recommendations

# Performance Optimization
enable_cloudfront_distribution = true        # CDN for static assets
cloudfront_price_class = "PriceClass_100"   # Use only edge locations in regions
enable_redis_cluster = false                 # Using Upstash Redis instead

# Alerting Configuration
enable_slack_alerts = false                  # Can be enabled with webhook
enable_email_alerts = true                   # Email alerts for critical issues
enable_sms_alerts = false                    # SMS for critical alerts (can be enabled)

# Maintenance and Updates
maintenance_window = "sun:03:00-sun:06:00"   # 3-hour maintenance window
auto_minor_version_upgrade = true            # Automatic minor version updates
preferred_backup_window = "02:00-03:00"      # 1-hour backup window

# Tags (Production)
tags = {
  Environment = "prod"
  Application = "turtil-backend"
  ManagedBy   = "terraform"
  CostCenter  = "prod"
  Owner       = "platform-team"
  Criticality = "high"
  Compliance  = "required"
  Backup      = "required"
  Monitoring  = "comprehensive"
}