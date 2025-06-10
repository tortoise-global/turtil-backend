# Terraform configuration for Turtil Backend AWS infrastructure

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Configure the AWS Provider
provider "aws" {
  region = var.aws_region
}

# Data source to get current AWS region
data "aws_region" "current" {}

# Data source to get current AWS caller identity
data "aws_caller_identity" "current" {}

# S3 bucket for file uploads
resource "aws_s3_bucket" "turtil_uploads" {
  bucket = var.s3_bucket_name

  tags = {
    Name        = "Turtil File Uploads"
    Environment = var.environment
    Project     = "Turtil Backend"
  }
}

# S3 bucket versioning
resource "aws_s3_bucket_versioning" "turtil_uploads_versioning" {
  bucket = aws_s3_bucket.turtil_uploads.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 bucket server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "turtil_uploads_encryption" {
  bucket = aws_s3_bucket.turtil_uploads.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 bucket public access block
resource "aws_s3_bucket_public_access_block" "turtil_uploads_pab" {
  bucket = aws_s3_bucket.turtil_uploads.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 bucket CORS configuration
resource "aws_s3_bucket_cors_configuration" "turtil_uploads_cors" {
  bucket = aws_s3_bucket.turtil_uploads.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "DELETE", "HEAD"]
    allowed_origins = var.cors_origins
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# S3 bucket lifecycle configuration
resource "aws_s3_bucket_lifecycle_configuration" "turtil_uploads_lifecycle" {
  bucket = aws_s3_bucket.turtil_uploads.id

  rule {
    id     = "delete_incomplete_multipart_uploads"
    status = "Enabled"

    filter {
      prefix = ""
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }

  rule {
    id     = "transition_to_ia"
    status = "Enabled"

    filter {
      prefix = ""
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
}

# Note: IAM user creation removed due to insufficient permissions
# Use existing IAM user credentials or ask admin to create IAM user manually
# 
# If you need to create IAM resources, ask your AWS administrator to grant:
# - iam:CreateUser
# - iam:AttachUserPolicy  
# - iam:CreateAccessKey
# 
# For now, configure your AWS credentials manually and use them in your application