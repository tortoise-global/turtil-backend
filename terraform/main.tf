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

# Security Group for EC2 (allow HTTP and SSH)
resource "aws_security_group" "dev_ec2" {
  name_prefix = "turtil-backend-dev-ec2-"
  vpc_id      = data.aws_vpc.default.id
  description = "Security group for dev EC2 instance"

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP traffic"
  }

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "FastAPI application (direct access)"
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH access"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = {
    Name        = "turtil-backend-dev-ec2-sg"
    Environment = "dev"
    Project     = "turtil-backend"
  }
}

# EC2 Instance for the application
resource "aws_instance" "dev_app" {
  ami           = "ami-0ad21ae1d0696ad58" # Ubuntu 22.04 LTS ARM64
  instance_type = "t4g.micro"
  
  vpc_security_group_ids = [aws_security_group.dev_ec2.id]
  
  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    ecr_repository_url = aws_ecr_repository.dev_app.repository_url
    aws_region        = "ap-south-1"
    environment       = "dev"
  }))
  
  tags = {
    Name        = "turtil-backend-dev"
    Environment = "dev"
    Project     = "turtil-backend"
  }
}

# Route 53 Hosted Zone (assuming turtil.co exists)
data "aws_route53_zone" "main" {
  name         = "turtil.co"
  private_zone = false
}

# Route 53 A Record for dev.api.turtil.co
resource "aws_route53_record" "dev_api" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = "dev.api.turtil.co"
  type    = "A"
  ttl     = 300
  records = [aws_instance.dev_app.public_ip]
  
  depends_on = [aws_instance.dev_app]
}

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

output "ec2_instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.dev_app.id
}

output "ec2_public_ip" {
  description = "EC2 instance public IP"
  value       = aws_instance.dev_app.public_ip
}

output "dev_api_url" {
  description = "Development API URL"
  value       = "http://dev.api.turtil.co"
}

output "route53_record" {
  description = "Route 53 record for dev API"
  value       = aws_route53_record.dev_api.fqdn
}

output "dev_instance_info" {
  description = "Development instance information"
  value = {
    instance_id = aws_instance.dev_app.id
    public_ip   = aws_instance.dev_app.public_ip
    api_url     = "http://dev.api.turtil.co"
    health_url  = "http://dev.api.turtil.co/health"
    docs_url    = "http://dev.api.turtil.co/docs"
    direct_url  = "http://${aws_instance.dev_app.public_ip}:8000"
  }
}

data "aws_caller_identity" "current" {}