# ============================================================================
# DEV ENVIRONMENT CONFIGURATION
# ============================================================================
# Ultra cost-optimized configuration for dev environment
# Single EC2 instance without load balancer or auto scaling

# Environment Configuration
environment = "dev"
project_name = "turtil-backend-dev"

# Compute Configuration (Single Instance - No Auto Scaling)
instance_type = "t4g.micro"           # ARM Graviton2 for cost efficiency
enable_single_instance = true         # Use single EC2 instance instead of ASG
enable_spot_instances = true          # Use spot instances for maximum cost savings
enable_load_balancer = false          # No ALB for dev (cost savings)

# Database Configuration (Development)
database_instance_class = "db.t4g.micro"    # Cheapest ARM-based option
database_allocated_storage = 20              # Minimal storage
database_backup_retention = 1                # 1-day backup retention
database_multi_az = false                    # Single-AZ for cost savings
enable_deletion_protection = false           # Allow easy cleanup
database_name = "turtil_backend_dev"

# Storage Configuration 
s3_bucket_prefix = "turtil-backend-dev"           # S3 bucket prefix
enable_s3_versioning = false                 # Disable versioning for cost
s3_lifecycle_enabled = true                  # Enable lifecycle for cleanup
s3_transition_to_ia_days = 30                # Move to IA after 30 days
s3_expiration_days = 90                      # Delete after 90 days

# Container Registry Configuration
ecr_repository_name = "turtil-backend-dev"        # ECR repository name
ecr_image_tag_mutability = "MUTABLE"
ecr_max_image_count = 5                      # Keep fewer images

# Monitoring and Logging (Minimal)
enable_detailed_monitoring = false           # Basic monitoring only
cloudwatch_log_retention = 7                 # 7-day log retention
enable_performance_insights = false          # Disable for cost savings

# Security Configuration (Development)
enable_waf = false                           # Skip WAF for dev
ssl_certificate_arn = ""                     # No SSL for dev
enable_backup_encryption = false             # Skip encryption for cost

# Network Configuration
vpc_cidr = "10.0.0.0/16"
availability_zones = ["ap-south-1a", "ap-south-1b"]

# Auto Scaling Configuration
scale_up_threshold = 80                      # Scale up at 80% CPU
scale_down_threshold = 30                    # Scale down at 30% CPU
scale_up_adjustment = 1                      # Add 1 instance
scale_down_adjustment = -1                   # Remove 1 instance

# Application Configuration
debug_mode = true                            # Enable debug mode
log_level = "DEBUG"                          # Verbose logging for dev

# Tags
tags = {
  Environment = "dev"
  Application = "turtil-backend-dev"
  ManagedBy   = "terraform"
  CostCenter  = "dev"
  Owner       = "dev-team"
}