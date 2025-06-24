# ============================================================================
# SIMPLIFIED DEV ENVIRONMENT - CORE RESOURCES ONLY
# ============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.53.0"
    }
  }
  backend "s3" {
    bucket = "turtil-backend-terraform"
    key    = "simple-dev/terraform.tfstate"
    region = "ap-south-1"
  }
}

provider "aws" {
  region = "ap-south-1"
}

# Random suffix for unique bucket names
resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}

# PostgreSQL RDS Database
resource "aws_db_instance" "dev_database" {
  identifier             = "turtil-backend-dev"
  engine                 = "postgres"
  engine_version         = "15.7"
  instance_class         = "db.t4g.micro"
  allocated_storage      = 20
  max_allocated_storage  = 100
  
  db_name  = "turtil_backend_dev"
  username = "turtiluser"
  password = "DevPassword123!"
  
  publicly_accessible = true
  db_subnet_group_name   = aws_db_subnet_group.main.name
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  skip_final_snapshot = true
  deletion_protection = false
  
  tags = {
    Name        = "turtil-backend-dev-database"
    Environment = "dev"
    Project     = "turtil-backend"
  }
}

# S3 Bucket for file storage
resource "aws_s3_bucket" "dev_storage" {
  bucket = "turtil-backend-dev-storage-${random_string.bucket_suffix.result}"
  
  tags = {
    Name        = "turtil-backend-dev-storage"
    Environment = "dev"
    Project     = "turtil-backend"
  }
}

resource "aws_s3_bucket_versioning" "dev_storage" {
  bucket = aws_s3_bucket.dev_storage.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "dev_storage" {
  bucket = aws_s3_bucket.dev_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "dev_storage" {
  bucket = aws_s3_bucket.dev_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ECR Repository
resource "aws_ecr_repository" "dev_app" {
  name                 = "turtil-backend-dev"
  image_tag_mutability = "MUTABLE"
  
  image_scanning_configuration {
    scan_on_push = false
  }
  
  tags = {
    Name        = "turtil-backend-dev-ecr"
    Environment = "dev"
    Project     = "turtil-backend"
  }
}

resource "aws_ecr_lifecycle_policy" "dev_app" {
  repository = aws_ecr_repository.dev_app.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 images"
      selection = {
        tagStatus     = "tagged"
        tagPrefixList = ["v"]
        countType     = "imageCountMoreThan"
        countNumber   = 10
      }
      action = {
        type = "expire"
      }
    }]
  })
}

# Default VPC and Subnets
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# DB Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "turtil-backend-dev-db-subnet-group"
  subnet_ids = data.aws_subnets.default.ids

  tags = {
    Name        = "turtil-backend-dev-db-subnet-group"
    Environment = "dev"
    Project     = "turtil-backend"
  }
}

# Note: Using default security group for dev environment to avoid permission issues

# Outputs
output "database_url" {
  description = "Complete database URL for application"
  value       = "postgresql+asyncpg://${aws_db_instance.dev_database.username}:DevPassword123!@${aws_db_instance.dev_database.endpoint}/${aws_db_instance.dev_database.db_name}"
  sensitive   = true
}

output "database_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.dev_database.endpoint
}

output "s3_bucket_name" {
  description = "S3 bucket name for file storage"
  value       = aws_s3_bucket.dev_storage.bucket
}

output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.dev_app.repository_url
}

output "aws_account_id" {
  description = "AWS Account ID"
  value       = data.aws_caller_identity.current.account_id
}

data "aws_caller_identity" "current" {}