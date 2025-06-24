# Environment Management Guide

This guide explains how to manage environment-specific configurations, database URLs, S3 buckets, and Upstash Redis connections across development, test, and production environments.

## 📁 Environment Files Overview

The project uses environment-specific `.env` files to manage configurations:

```
📦 turtil-backend/
├── .env.dev          # Development environment
├── .env.test         # Test environment  
├── .env.prod         # Production environment
└── terraform/
    ├── environments/
    │   ├── dev.tfvars    # Terraform variables for dev
    │   ├── test.tfvars   # Terraform variables for test
    │   └── prod.tfvars   # Terraform variables for prod
    └── scripts/
        ├── loadenv.sh       # Load .env into Terraform
        ├── populate-env.sh  # Populate .env from Terraform
        ├── local-plan.sh    # Plan deployment
        └── local-apply.sh   # Apply deployment
```

## 🌍 Environment Configurations

### Development (.env.dev)
- **Database**: `turtil-backend-dev` (RDS t4g.micro single-AZ)
- **Architecture**: Single EC2 instance (no load balancer)
- **Cost**: ~$15-20/month
- **Features**: Debug mode, relaxed rate limiting, mock services

### Test (.env.test)
- **Database**: `turtil-backend-test` (RDS t4g.micro)
- **Architecture**: Auto Scaling Group + Load Balancer
- **Cost**: ~$30-35/month
- **Features**: Production-like testing, load testing support

### Production (.env.prod)
- **Database**: `turtil-backend-prod` (Aurora Serverless v2)
- **Architecture**: Auto Scaling Group + Load Balancer + CloudFront
- **Cost**: ~$60-80/month
- **Features**: High availability, full monitoring, encryption

## 🚀 Deployment Workflow

### 1. Initial Setup

First, ensure you have the base environment files:

```bash
# Check if environment files exist
ls -la .env.*

# If missing, they should be created with placeholder values
# (They are included in the repository)
```

### 2. Deploy Infrastructure

Choose your environment and deploy:

```bash
# Development Environment
cd terraform
./scripts/local-plan.sh dev
./scripts/local-apply.sh dev

# Test Environment  
./scripts/local-plan.sh test
./scripts/local-apply.sh test

# Production Environment
./scripts/local-plan.sh prod
./scripts/local-apply.sh prod
```

### 3. Populate Environment Files

After successful deployment, populate your `.env` files with actual values:

```bash
# Populate development environment
./scripts/populate-env.sh dev

# Populate test environment
./scripts/populate-env.sh test

# Populate production environment
./scripts/populate-env.sh prod

# Or populate all at once
./scripts/populate-env.sh all
```

### 4. Manual Configuration

Some values need to be manually configured:

#### AWS Credentials
```bash
# Update in .env.dev, .env.test, .env.prod
AWS_ACCESS_KEY_ID=your_actual_access_key
AWS_SECRET_ACCESS_KEY=your_actual_secret_key
```

#### Upstash Redis
```bash
# Get these from your Upstash console
UPSTASH_REDIS_URL=your_upstash_url
UPSTASH_REDIS_TOKEN=your_upstash_token
```

#### Production Security
```bash
# .env.prod - Generate strong secret keys
SECRET_KEY=very_secure_production_key_here
```

## 🗄️ Database URL Population

Database URLs are automatically populated by Terraform in this format:

```bash
# Development
DATABASE_URL=postgresql+asyncpg://turtiluser:generated_password@dev-rds-endpoint:5432/turtil-backend-dev

# Test
DATABASE_URL=postgresql+asyncpg://turtiluser:generated_password@test-rds-endpoint:5432/turtil-backend-test

# Production (Aurora Serverless v2)
DATABASE_URL=postgresql+asyncpg://turtiluser:generated_password@prod-aurora-endpoint:5432/turtil-backend-prod
```

## 🪣 S3 Bucket Configuration

S3 buckets are automatically created and configured:

```bash
# Development
S3_BUCKET_NAME=turtil-backend-dev-storage-randomsuffix

# Test
S3_BUCKET_NAME=turtil-backend-test-storage-randomsuffix

# Production
S3_BUCKET_NAME=turtil-backend-prod-storage-randomsuffix
```

## 🔧 How the Scripts Work

### loadenv.sh
```bash
# Usage
source ./scripts/loadenv.sh dev    # Load development environment
source ./scripts/loadenv.sh test   # Load test environment
source ./scripts/loadenv.sh prod   # Load production environment

# What it does:
# 1. Reads .env.{environment} file
# 2. Exports all variables as TF_VAR_* for Terraform
# 3. Sets environment-specific flags
# 4. Validates environment file exists
```

### populate-env.sh
```bash
# Usage
./scripts/populate-env.sh dev     # Update .env.dev with actual values
./scripts/populate-env.sh test    # Update .env.test with actual values
./scripts/populate-env.sh prod    # Update .env.prod with actual values
./scripts/populate-env.sh all     # Update all environment files

# What it does:
# 1. Extracts database URLs from Terraform outputs
# 2. Gets S3 bucket names from Terraform state
# 3. Updates .env files with actual values
# 4. Creates backup files before modification
```

### local-plan.sh & local-apply.sh
```bash
# Usage
./scripts/local-plan.sh dev      # Plan development infrastructure
./scripts/local-apply.sh dev     # Apply development infrastructure

# What they do:
# 1. Load environment-specific variables
# 2. Switch to correct Terraform workspace
# 3. Use appropriate .tfvars file
# 4. Apply environment-specific configurations
```

## 🔄 Environment Switching

To switch between environments:

```bash
# Switch to development
cd terraform
terraform workspace select dev
source ./scripts/loadenv.sh dev

# Switch to test
terraform workspace select test  
source ./scripts/loadenv.sh test

# Switch to production
terraform workspace select prod
source ./scripts/loadenv.sh prod
```

## 📊 Verifying Deployment

After deployment, verify your environment:

```bash
# Check Terraform outputs
terraform output

# For development (single instance)
terraform output dev_instance_info

# For test/production (load balancer)
terraform output example_alb_dns_name

# Check health endpoints
# Development: http://<instance-ip>:8000/health
# Test/Prod:   http://<alb-dns>/health
```

## 🔒 Security Considerations

### Development
- Uses placeholder secrets (not for production)
- Debug mode enabled
- Relaxed security settings
- Cost optimized with spot instances

### Test
- Production-like security
- Real encryption and security groups
- Suitable for integration testing
- No debug mode

### Production
- Maximum security configuration
- Encrypted storage and backups
- Strong authentication requirements
- Comprehensive monitoring

## 📝 Environment File Templates

### .env.dev Template
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/turtil-backend-dev
S3_BUCKET_NAME=turtil-backend-dev-storage-suffix
UPSTASH_REDIS_URL=redis://your-dev-redis-url
DEBUG=true
LOG_LEVEL=DEBUG
```

### .env.test Template
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/turtil-backend-test
S3_BUCKET_NAME=turtil-backend-test-storage-suffix
UPSTASH_REDIS_URL=redis://your-test-redis-url
DEBUG=false
LOG_LEVEL=INFO
```

### .env.prod Template
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/turtil-backend-prod
S3_BUCKET_NAME=turtil-backend-prod-storage-suffix
UPSTASH_REDIS_URL=redis://your-prod-redis-url
DEBUG=false
LOG_LEVEL=INFO
SECRET_KEY=very_secure_production_key
```

## 🆘 Troubleshooting

### Database URL Not Populated
```bash
# Check if Terraform deployment succeeded
terraform output database_endpoint

# Re-run populate script
./scripts/populate-env.sh dev
```

### S3 Bucket Access Issues
```bash
# Verify bucket exists
aws s3 ls | grep turtil-backend

# Check bucket name in environment
echo $S3_BUCKET_NAME
```

### Environment File Missing
```bash
# Copy from template
cp .env.dev .env.test

# Or restore from backup
cp .env.dev.backup.20241224_120000 .env.dev
```

### Terraform Workspace Issues
```bash
# List workspaces
terraform workspace list

# Create missing workspace
terraform workspace new dev

# Switch workspace
terraform workspace select dev
```

## 🚀 Quick Start Commands

```bash
# Deploy development environment
cd terraform
./scripts/local-plan.sh dev
./scripts/local-apply.sh dev
./scripts/populate-env.sh dev

# Deploy test environment
./scripts/local-plan.sh test
./scripts/local-apply.sh test  
./scripts/populate-env.sh test

# Deploy production environment
./scripts/local-plan.sh prod
./scripts/local-apply.sh prod
./scripts/populate-env.sh prod
```

This environment management system ensures clean separation between development, testing, and production while automating the population of database URLs, S3 bucket names, and other infrastructure-dependent configuration values.