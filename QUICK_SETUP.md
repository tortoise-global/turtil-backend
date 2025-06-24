# 🚀 Quick Setup Guide - Get Running Fast

Since the full Terraform setup has complex dependencies, here's how to get up and running quickly:

## 🎯 **Option 1: Manual AWS Resource Creation (Fastest)**

### **Create Resources Manually:**

```bash
# 1. Create RDS Database
aws rds create-db-instance \
  --db-instance-identifier turtil-backend-dev \
  --db-instance-class db.t4g.micro \
  --engine postgres \
  --master-username turtiluser \
  --master-user-password CHANGE_THIS_PASSWORD \
  --allocated-storage 20 \
  --db-name turtil_backend_dev

# 2. Create S3 Bucket
aws s3 mb s3://turtil-backend-dev-storage-$(date +%s)

# 3. Create ECR Repository
aws ecr create-repository --repository-name turtil-backend-dev
```

### **Update .env.dev with actual values:**

```bash
# After resources are created, update .env.dev:
DATABASE_URL=postgresql+asyncpg://turtiluser:CHANGE_THIS_PASSWORD@your-rds-endpoint:5432/turtil_backend_dev
S3_BUCKET_NAME=turtil-backend-dev-storage-1234567890
```

## 🎯 **Option 2: Simplified Terraform (Recommended)**

### **Create minimal main.tf:**

```hcl
# Create a simplified main.tf with just core resources
terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
  backend "s3" {
    bucket = "turtil-backend-terraform"
    key    = "simple-setup/terraform.tfstate"
    region = "ap-south-1"
  }
}

provider "aws" {
  region = "ap-south-1"
}

# Simple RDS instance
resource "aws_db_instance" "main" {
  identifier     = "turtil-backend-${var.environment}"
  engine         = "postgres"
  instance_class = "db.t4g.micro"
  allocated_storage = 20
  db_name        = "turtil_backend_${replace(var.environment, "-", "_")}"
  username       = "turtiluser"
  password       = "CHANGE_THIS_PASSWORD"
  skip_final_snapshot = true
}

# Simple S3 bucket
resource "aws_s3_bucket" "storage" {
  bucket = "turtil-backend-${var.environment}-storage-${random_string.suffix.result}"
}

resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

# Simple ECR repository
resource "aws_ecr_repository" "app" {
  name = "turtil-backend-${var.environment}"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

# Outputs
output "database_url" {
  value = "postgresql+asyncpg://${aws_db_instance.main.username}:CHANGE_THIS_PASSWORD@${aws_db_instance.main.endpoint}/${aws_db_instance.main.db_name}"
}

output "s3_bucket_name" {
  value = aws_s3_bucket.storage.bucket
}

output "ecr_repository_url" {
  value = aws_ecr_repository.app.repository_url
}
```

## 🎯 **Option 3: Use Existing Complex Setup (Long-term)**

The current Terraform setup needs these missing variables added to `variables.tf`:

- `app_database_url`, `app_secret_key`, `app_algorithm`
- `app_access_token_expire_minutes`, `app_version`, `app_debug`
- `app_log_level`, `app_rate_limit_calls`, `app_rate_limit_period`
- And many more application-specific variables

## 🚀 **Immediate Action Plan:**

### **Right Now:**

1. **Start local development** with Docker:
   ```bash
   cd db && docker-compose up -d
   export ENV_FILE=.env.local
   python run.py
   ```

### **For AWS Testing:**

1. **Create basic resources manually** (Option 1 above)
2. **Update .env.dev** with real values
3. **Test with**: `export ENV_FILE=.env.dev && python run.py`

### **For Production Infrastructure:**

1. **Fix the complex Terraform setup** by adding all missing variables
2. **Or use the simplified Terraform** (Option 2 above) as a starting point

## 📋 **Environment Status:**

✅ **Local (.env.local)**: Ready - uses Docker services  
⚠️ **Dev (.env.dev)**: Needs AWS resources  
⚠️ **Test (.env.test)**: Needs AWS resources  
⚠️ **Prod (.env.prod)**: Needs AWS resources

## 🎯 **Next Steps:**

1. **Start with local development** (works now)
2. **Create basic AWS resources** manually for testing
3. **Gradually build up** to full infrastructure

The environment management system is ready - we just need to populate the AWS resource URLs!

export ENV_FILE=.env.dev
source venv/bin/activate
python run.py
