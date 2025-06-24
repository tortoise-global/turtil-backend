# ============================================================================
# TEST ENVIRONMENT CONFIGURATION
# ============================================================================
# Production-like configuration for testing environment
# Includes load balancer and minimal auto scaling

# Environment Configuration
environment = "test"
project_name = "turtil-backend"

# Compute Configuration (Minimal Production-like)
instance_type = "t4g.micro"           # ARM Graviton2 for cost efficiency
min_size = 1                          # Minimal baseline
max_size = 2                          # Limited scaling for testing
desired_capacity = 1                  # Start with single instance
enable_spot_instances = false         # Use on-demand for stability
enable_load_balancer = true           # Include ALB for prod-like testing

# Database Configuration (Testing)
database_instance_class = "db.t4g.micro"    # ARM-based for cost efficiency
database_allocated_storage = 20              # Standard storage
database_backup_retention = 7                # 7-day backup retention
database_multi_az = false                    # Single-AZ for cost optimization
enable_deletion_protection = false           # Allow cleanup after testing
database_name = "turtil-backend-test"

# Storage Configuration
s3_bucket_prefix = "turtil-backend"           # S3 bucket prefix
enable_s3_versioning = true                  # Enable versioning for testing
s3_lifecycle_enabled = true                  # Enable lifecycle management
s3_transition_to_ia_days = 30                # Move to IA after 30 days
s3_transition_to_glacier_days = 90           # Move to Glacier after 90 days
s3_expiration_days = 365                     # Keep for 1 year

# Container Registry Configuration
ecr_repository_name = "turtil-backend"        # ECR repository name
ecr_image_tag_mutability = "MUTABLE"
ecr_max_image_count = 10                     # Keep more images for testing

# Monitoring and Logging (Enhanced)
enable_detailed_monitoring = true            # Enable detailed monitoring
cloudwatch_log_retention = 14                # 14-day log retention
enable_performance_insights = false          # Basic performance monitoring

# Security Configuration (Testing)
enable_waf = false                           # Basic security for testing
ssl_certificate_arn = ""                     # Test with HTTP
enable_backup_encryption = true              # Enable encryption

# Network Configuration
vpc_cidr = "10.1.0.0/16"
availability_zones = ["ap-south-1a", "ap-south-1b"]

# Auto Scaling Configuration
scale_up_threshold = 70                      # More sensitive scaling for testing
scale_down_threshold = 25                    # Aggressive scale down
scale_up_adjustment = 1                      # Add 1 instance
scale_down_adjustment = -1                   # Remove 1 instance

# Load Testing Configuration
max_concurrent_users = 100                   # Support moderate load testing
connection_draining_timeout = 60             # 1-minute draining

# Application Configuration
debug_mode = false                           # Production-like behavior
log_level = "INFO"                           # Standard logging level

# Testing Specific Features
enable_test_data_seeding = true              # Allow test data
reset_database_on_deploy = false             # Preserve test data
enable_mock_external_services = true         # Mock external APIs

# Performance Testing
enable_load_testing = true                   # Support for load testing tools
enable_stress_testing = false               # Disable stress testing by default

# Tags
tags = {
  Environment = "test"
  Application = "turtil-backend"
  ManagedBy   = "terraform"
  CostCenter  = "test"
  Owner       = "test-team"
  Purpose     = "automated-testing"
}