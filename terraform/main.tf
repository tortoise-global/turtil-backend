# ============================================================================
# MODULAR TERRAFORM CONFIGURATION - TURTIL BACKEND
# ============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.53.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
  }
  backend "s3" {
    bucket = "turtil-backend-terraform"
    key    = "modular-dev/terraform.tfstate"
    region = "ap-south-1"
  }
}

provider "aws" {
  region = var.aws_region
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_route53_zone" "main" {
  name         = "turtil.co"
  private_zone = false
}

# ============================================================================
# VPC MODULE
# ============================================================================

module "vpc" {
  source = "./modules/vpc"
  
  project_name    = var.project_name
  environment     = var.app_environment
  vpc_cidr        = "10.0.0.0/16"
  
  public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnet_cidrs = ["10.0.10.0/24", "10.0.11.0/24"]
  availability_zones   = ["ap-south-1a", "ap-south-1b"]
  
  # Allow external DB access for development
  allow_external_db_access = var.app_environment == "dev"
}

# ============================================================================
# IAM MODULE
# ============================================================================

module "iam" {
  source = "./modules/iam"
  
  project_name = var.project_name
  environment  = var.app_environment
  
  s3_bucket_arn         = module.s3_storage.bucket_arn
  enable_ses_access     = true
  enable_cloudwatch_logs = true
}

# ============================================================================
# S3 MODULES
# ============================================================================

# Main storage bucket
module "s3_storage" {
  source = "./modules/s3"
  
  project_name   = var.project_name
  environment    = var.app_environment
  bucket_purpose = "storage"
  
  versioning_enabled = true
  
  # Enable public access for development file uploads
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
  
  # CORS configuration for file uploads
  cors_rules = [
    {
      allowed_methods = ["GET", "POST", "PUT"]
      allowed_origins = ["*"]
      allowed_headers = ["*"]
      max_age_seconds = 3600
    }
  ]
  
  
  # Lifecycle rules
  lifecycle_rules = [
    {
      id     = "delete_incomplete_uploads"
      status = "Enabled"
      expiration = {
        days = 7
      }
    }
  ]
}

# ============================================================================
# ECR MODULE
# ============================================================================

module "ecr" {
  source = "./modules/ecr"
  
  project_name         = var.project_name
  environment          = var.app_environment
  image_tag_mutability = "MUTABLE"
  scan_on_push         = false
  
  # Lifecycle policy
  create_lifecycle_policy = true
  max_image_count        = 10
  tag_prefix_list        = ["v", "dev", "latest"]
  untagged_image_days    = 1
}

# S3 bucket policy for public read access
resource "aws_s3_bucket_policy" "storage_policy" {
  bucket = module.s3_storage.bucket_name
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${module.s3_storage.bucket_arn}/*"
      }
    ]
  })
  
  depends_on = [module.s3_storage]
}

# ============================================================================
# RDS MODULE
# ============================================================================

module "rds" {
  source = "./modules/rds"
  
  project_name    = var.project_name
  environment     = var.app_environment
  postgres_version = "15.7"
  instance_class   = "db.t4g.micro"
  
  allocated_storage     = 20
  max_allocated_storage = 100
  
  database_name = replace("${var.project_name}_${var.app_environment}", "-", "_")
  username      = var.app_db_username
  password      = var.app_db_password
  
  # Use public subnet group for development external access
  db_subnet_group_name = var.app_environment == "dev" ? module.vpc.public_db_subnet_group_name : module.vpc.private_db_subnet_group_name
  security_group_ids   = [module.vpc.rds_security_group_id]
  publicly_accessible  = var.app_environment == "dev"
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  skip_final_snapshot = true
  deletion_protection = false
  
  # Performance and monitoring
  performance_insights_enabled = false
  monitoring_interval         = 0
  storage_encrypted          = true
  multi_az                   = false
}

# ============================================================================
# EC2 MODULE
# ============================================================================

module "ec2" {
  source = "./modules/ec2"
  
  project_name  = var.project_name
  environment   = var.app_environment
  ami_id        = var.custom_ami_id
  instance_type = "t4g.micro"
  key_name      = "turtil-backend"
  
  subnet_id                   = module.vpc.public_subnet_ids[0]
  security_group_ids          = [module.vpc.ec2_security_group_id]
  iam_instance_profile_name   = module.iam.ec2_instance_profile_name
  
  # User data for application setup
  user_data_script = "${path.module}/user_data.sh"
  user_data_vars = {
    ecr_repository_url = module.ecr.repository_url
    aws_region        = var.aws_region
    environment       = var.app_environment
    database_url      = module.rds.database_url
    s3_bucket_name    = module.s3_storage.bucket_name
    
    # Database credentials
    app_db_username   = var.app_db_username
    app_db_password   = var.app_db_password
    
    # Application configuration
    app_secret_key    = var.app_secret_key
    algorithm         = var.app_algorithm
    access_token_expire_minutes = var.app_access_token_expire_minutes
    refresh_token_expire_minutes = var.app_refresh_token_expire_minutes
    otp_expiry_minutes = var.app_otp_expiry_minutes
    otp_max_attempts  = var.app_otp_max_attempts
    dev_otp          = var.app_dev_otp
    cors_origins     = var.app_cors_origins
    allowed_hosts    = var.app_allowed_hosts
    rate_limit_calls = var.app_rate_limit_calls
    rate_limit_period = var.app_rate_limit_period
    
    # Redis configuration
    upstash_redis_url = var.app_upstash_redis_url
    upstash_redis_token = var.app_upstash_redis_token
    redis_user_cache_ttl = var.app_redis_user_cache_ttl
    redis_blacklist_ttl = var.app_redis_blacklist_ttl
    
    # AWS services
    aws_access_key_id = var.app_aws_access_key_id
    aws_secret_access_key = var.app_aws_secret_access_key
    aws_ses_from_email = var.app_aws_ses_from_email
    custom_ami_id = var.custom_ami_id
  }
  
  # Storage configuration
  root_volume_type      = "gp3"
  root_volume_size      = 20
  root_volume_encrypted = true
  
  # Monitoring
  detailed_monitoring       = false
  enable_cloudwatch_alarms = false
  
  additional_tags = {
    Application = "turtil-backend"
    Terraform   = "true"
  }
}

# ============================================================================
# ROUTE 53 RECORDS
# ============================================================================

resource "aws_route53_record" "dev_api" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = "${var.app_environment}.api.turtil.co"
  type    = "A"
  ttl     = 300
  records = [module.ec2.public_ip]
  
  depends_on = [module.ec2]
}

# ============================================================================
# OUTPUTS
# ============================================================================

output "infrastructure_info" {
  description = "Complete infrastructure information"
  value = {
    # VPC
    vpc_id = module.vpc.vpc_id
    public_subnet_ids = module.vpc.public_subnet_ids
    private_subnet_ids = module.vpc.private_subnet_ids
    
    # Database
    database_endpoint = module.rds.db_instance_endpoint
    database_url     = module.rds.database_url
    
    # Storage
    s3_bucket_name = module.s3_storage.bucket_name
    
    # Container Registry
    ecr_repository_url = module.ecr.repository_url
    
    # Compute
    ec2_instance_id = module.ec2.instance_id
    ec2_public_ip   = module.ec2.public_ip
    
    # Application URLs
    api_url     = "http://${var.app_environment}.api.turtil.co"
    health_url  = "http://${var.app_environment}.api.turtil.co/health"
    docs_url    = "http://${var.app_environment}.api.turtil.co/docs"
    direct_url  = "http://${module.ec2.public_ip}:8000"
  }
  sensitive = true
}

# Legacy compatibility outputs
output "database_url" {
  description = "Complete database URL for application"
  value       = module.rds.database_url
  sensitive   = true
}

output "database_endpoint" {
  description = "RDS instance endpoint"
  value       = module.rds.db_instance_endpoint
}

output "s3_bucket_name" {
  description = "S3 bucket name for file storage"
  value       = module.s3_storage.bucket_name
}

output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = module.ecr.repository_url
}

output "aws_account_id" {
  description = "AWS Account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "ec2_instance_id" {
  description = "EC2 instance ID"
  value       = module.ec2.instance_id
}

output "ec2_public_ip" {
  description = "EC2 instance public IP"
  value       = module.ec2.public_ip
}

output "dev_api_url" {
  description = "Development API URL"
  value       = "http://${var.app_environment}.api.turtil.co"
}

output "route53_record" {
  description = "Route 53 record for dev API"
  value       = aws_route53_record.dev_api.fqdn
}

output "dev_instance_info" {
  description = "Development instance information"
  value = {
    instance_id = module.ec2.instance_id
    public_ip   = module.ec2.public_ip
    api_url     = "http://${var.app_environment}.api.turtil.co"
    health_url  = "http://${var.app_environment}.api.turtil.co/health"
    docs_url    = "http://${var.app_environment}.api.turtil.co/docs"
    direct_url  = "http://${module.ec2.public_ip}:8000"
  }
}