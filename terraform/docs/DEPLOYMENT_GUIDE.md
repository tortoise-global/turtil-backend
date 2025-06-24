# Multi-Environment Deployment Guide

This guide explains how to deploy the Turtil Backend infrastructure across development, testing, and production environments using the new multi-environment Terraform configuration.

## 🏗️ Infrastructure Overview

The new infrastructure supports three environments with environment-specific resource naming and configurations:

- **Development**: Cost-optimized for local development
- **Testing**: Production-like configuration for QA
- **Production**: High-availability Aurora Serverless v2 with enhanced monitoring

## 📋 Prerequisites

1. **AWS CLI configured** with appropriate permissions
2. **Terraform installed** (version 1.5+)
3. **Environment variables** configured (see below)
4. **S3 backend bucket** for Terraform state (created automatically)

## 🔧 Environment Variables

Create environment-specific `.env` files or export these variables:

### Required Variables
```bash
# AWS Configuration
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_REGION="ap-south-1"

# Database Configuration
export TF_VAR_database_name="turtil_development"  # or turtil_testing, turtil_production

# S3 Configuration
export TF_VAR_s3_bucket_prefix="turtil-backend"

# ECR Configuration
export TF_VAR_ecr_account_id="your-aws-account-id"
export TF_VAR_ecr_repository_name="turtil-backend-development"  # environment-specific
```

## 🚀 Deployment Steps

### 1. Initialize Terraform (First Time Only)

```bash
cd terraform-files
terraform init
```

### 2. Create and Select Workspace

```bash
# Development
terraform workspace new development
terraform workspace select development

# Testing
terraform workspace new testing
terraform workspace select testing

# Production
terraform workspace new production
terraform workspace select production
```

### 3. Deploy Infrastructure

#### Development Environment
```bash
terraform workspace select development
terraform plan -var-file="environments/development.tfvars"
terraform apply -var-file="environments/development.tfvars"
```

#### Testing Environment
```bash
terraform workspace select testing
terraform plan -var-file="environments/testing.tfvars"
terraform apply -var-file="environments/testing.tfvars"
```

#### Production Environment
```bash
terraform workspace select production
terraform plan -var-file="environments/production.tfvars"
terraform apply -var-file="environments/production.tfvars"
```

## 📊 Resource Naming Convention

Resources are automatically named with the pattern: `{project-name}-{environment}-{resource-type}`

### Examples:
- **Database**: `turtil-backend-development-postgres`
- **S3 Buckets**: 
  - `turtil-backend-development-storage`
  - `turtil-backend-development-logs`
  - `turtil-backend-development-terraform-state`
- **ECR Repository**: `turtil-backend-development`
- **Security Groups**: `turtil-backend-development-app-sg`

## 💾 Database Configuration by Environment

### Development
- **Type**: RDS PostgreSQL 15
- **Instance**: db.t4g.micro (ARM Graviton2)
- **Storage**: 20GB gp3
- **Backup**: 1-day retention
- **Multi-AZ**: Disabled
- **Cost**: ~$9-11/month

### Testing
- **Type**: RDS PostgreSQL 15
- **Instance**: db.t4g.micro (ARM Graviton2)
- **Storage**: 20GB gp3
- **Backup**: 7-day retention
- **Multi-AZ**: Disabled
- **Cost**: ~$10-12/month

### Production
- **Type**: Aurora Serverless v2 PostgreSQL 15
- **Capacity**: 0.5-32 ACU (auto-scaling)
- **Backup**: 30-day retention with point-in-time recovery
- **Multi-AZ**: Enabled
- **Encryption**: Enabled
- **Performance Insights**: Enabled
- **Cost**: ~$80-200/month (based on usage)

## 🪣 S3 Bucket Configuration

Each environment gets three buckets:
1. **App Storage**: For application file uploads
2. **Logs**: For application and access logs
3. **Terraform State**: For infrastructure state management

### Features by Environment:
- **Development**: Basic lifecycle (30→90 day transitions)
- **Testing**: Versioning + Intelligent Tiering
- **Production**: Versioning + Intelligent Tiering + Cross-region replication

## 🐳 Container Registry (ECR)

Environment-specific ECR repositories with:
- **Development**: 5 image limit, mutable tags
- **Testing**: 10 image limit, mutable tags
- **Production**: 20 image limit, immutable tags, enhanced scanning

## 🔐 Security Configuration

### Development
- Basic security groups
- No WAF
- Self-signed certificates
- Minimal monitoring

### Testing
- Enhanced security groups
- Basic SSL
- Standard monitoring
- Performance testing enabled

### Production
- Comprehensive security groups
- WAF enabled
- SSL/TLS with proper certificates
- Full monitoring and alerting
- Enhanced scanning and compliance

## 📱 Application Configuration

After deployment, update your application's environment variables:

```bash
# Get outputs from Terraform
terraform output application_environment_variables
```

Example output:
```json
{
  "DATABASE_URL": "postgresql+asyncpg://postgres:password@endpoint:5432/turtil_development",
  "S3_BUCKET_NAME": "turtil-backend-development-storage",
  "S3_BUCKET_PREFIX": "turtil-backend",
  "ECR_REPOSITORY_NAME": "turtil-backend-development",
  "ENVIRONMENT": "development"
}
```

## 🔄 CI/CD Integration

### GitHub Actions Variables

Add these secrets to your GitHub repository:

```bash
# AWS Credentials
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY

# Environment-specific variables
TF_VAR_database_name_development="turtil_development"
TF_VAR_database_name_testing="turtil_testing"
TF_VAR_database_name_production="turtil_production"

TF_VAR_ecr_repository_name_development="turtil-backend-development"
TF_VAR_ecr_repository_name_testing="turtil-backend-testing"
TF_VAR_ecr_repository_name_production="turtil-backend-production"
```

### Deployment Workflow

```yaml
name: Deploy Infrastructure

on:
  push:
    branches:
      - main      # Deploy to production
      - develop   # Deploy to testing
      - feature/* # Deploy to development

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v2
        with:
          terraform_version: 1.5.0
          
      - name: Terraform Init
        run: terraform init
        working-directory: terraform-files
        
      - name: Select Environment
        run: |
          if [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
            terraform workspace select production
            ENV_FILE="environments/production.tfvars"
          elif [[ "${{ github.ref }}" == "refs/heads/develop" ]]; then
            terraform workspace select testing
            ENV_FILE="environments/testing.tfvars"
          else
            terraform workspace select development
            ENV_FILE="environments/development.tfvars"
          fi
          echo "ENV_FILE=$ENV_FILE" >> $GITHUB_ENV
        working-directory: terraform-files
        
      - name: Terraform Plan
        run: terraform plan -var-file="$ENV_FILE"
        working-directory: terraform-files
        
      - name: Terraform Apply
        run: terraform apply -auto-approve -var-file="$ENV_FILE"
        working-directory: terraform-files
```

## 🏥 Health Checks

After deployment, verify your infrastructure:

```bash
# Get health check URLs
terraform output health_check_endpoints

# Test endpoints
curl http://your-load-balancer/health
curl http://your-load-balancer/health/detailed
curl http://your-load-balancer/info
```

## 💰 Cost Monitoring

### Expected Monthly Costs:

| Environment | Database | Compute | Storage | Total |
|------------|----------|---------|---------|-------|
| Development | $9-11 | $8-15 | $3-5 | $20-31 |
| Testing | $10-12 | $8-20 | $4-8 | $22-40 |
| Production | $80-200 | $70-140 | $15-30 | $165-370 |

### Cost Optimization Tips:
1. **Development**: Use spot instances when possible
2. **Testing**: Schedule start/stop for business hours only
3. **Production**: Monitor Aurora ACU usage and adjust limits

## 🔄 Switching Between Environments

```bash
# List available workspaces
terraform workspace list

# Switch to desired environment
terraform workspace select development
terraform workspace select testing
terraform workspace select production

# View current workspace
terraform workspace show
```

## 🗑️ Cleanup

To destroy an environment (⚠️ **Use with caution**):

```bash
# Select the environment
terraform workspace select development

# Destroy infrastructure
terraform destroy -var-file="environments/development.tfvars"

# Delete workspace (optional)
terraform workspace select default
terraform workspace delete development
```

## 🐛 Troubleshooting

### Common Issues:

1. **Terraform State Lock**: Wait or break lock if stuck
2. **Resource Already Exists**: Import existing resources
3. **Permission Denied**: Verify AWS credentials and permissions
4. **Backend Not Found**: Ensure S3 backend bucket exists

### Debug Commands:

```bash
# Verbose logging
export TF_LOG=DEBUG
terraform plan -var-file="environments/development.tfvars"

# Refresh state
terraform refresh -var-file="environments/development.tfvars"

# Show current state
terraform show

# List resources
terraform state list
```

## 📚 Additional Resources

- [Terraform Workspaces Documentation](https://www.terraform.io/docs/state/workspaces.html)
- [AWS Provider Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Aurora Serverless v2 Documentation](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.html)

## 🤝 Support

For issues with the infrastructure:
1. Check the troubleshooting section above
2. Review Terraform logs with `TF_LOG=DEBUG`
3. Verify AWS permissions and quotas
4. Contact the platform team for production issues