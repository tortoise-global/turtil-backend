# Local Terraform Deployment Guide

This guide explains how to deploy the Turtil Backend infrastructure locally using Terraform with environment variables from your `.env` file.

## Prerequisites

### 1. Required Tools
- **Terraform** v1.5.0+ ([Download](https://terraform.io/downloads))
- **AWS CLI** configured with credentials
- **Git** for version control

### 2. AWS Prerequisites
- AWS account with appropriate permissions (see `IAM_PERMISSIONS.md`)
- AWS CLI configured: `aws configure`
- Valid AWS credentials in your `.env` file

### 3. Environment Configuration
- Complete `.env` file in the project root
- All required environment variables configured (see `.env.example`)

## Quick Start

### 1. Navigate to Terraform Directory
```bash
cd terraform-files
```

### 2. Initialize Terraform
```bash
./local-init.sh
```
This will:
- Load environment variables from `.env`
- Initialize Terraform
- Create/select the `local` workspace

### 3. Plan Your Deployment
```bash
./local-plan.sh [environment]
```
Examples:
```bash
./local-plan.sh development  # Deploy development environment
./local-plan.sh production   # Deploy production environment
```

### 4. Apply Changes
```bash
./local-apply.sh [environment]
```
This will:
- Load environment variables
- Apply the planned changes
- Clean up the plan file

### 5. Check Outputs
```bash
terraform output
```

## Available Scripts

### `local-init.sh`
Initializes Terraform for local development:
- Loads `.env` variables
- Runs `terraform init`
- Creates/selects `local` workspace

### `local-plan.sh [environment]`
Plans infrastructure changes:
- **Environment**: `development` (default), `production`, `testing`
- Uses environment-specific `.tfvars` files
- Saves plan as `tfplan-local-{environment}`

### `local-apply.sh [environment]`
Applies planned changes:
- Requires confirmation
- Uses saved plan file
- Cleans up after completion

### `local-destroy.sh [environment]`
Destroys all resources:
- **⚠️ DANGEROUS**: Permanently destroys infrastructure
- Requires typing `DESTROY` to confirm
- Double confirmation required

## Environment Variables

The `loadenv.sh` script automatically maps `.env` variables to Terraform variables:

| .env Variable | Terraform Variable | Purpose |
|--------------|-------------------|---------|
| `DATABASE_URL` | `TF_VAR_app_database_url` | Database connection |
| `SECRET_KEY` | `TF_VAR_app_secret_key` | JWT secret |
| `PROJECT_NAME` | `TF_VAR_project_name` | Resource naming |
| `AWS_ACCESS_KEY_ID` | `TF_VAR_app_aws_access_key_id` | AWS credentials |
| `ECR_ACCOUNT_ID` | `TF_VAR_ecr_account_id` | Container registry |

## Workspaces

Local deployment uses the `local` workspace to separate state from CI/CD:

```bash
# View current workspace
terraform workspace show

# List all workspaces
terraform workspace list

# Switch workspace (manual)
terraform workspace select local
```

## Environment-Specific Deployments

### Development Environment
```bash
./local-plan.sh development
./local-apply.sh development
```
- Uses `environments/development.tfvars`
- Creates development-prefixed resources
- Optimized for cost (single instance, t4g.micro)

### Production Environment
```bash
./local-plan.sh production
./local-apply.sh production
```
- Uses `environments/production.tfvars`
- Creates production-prefixed resources
- Optimized for performance (Aurora Serverless, multi-AZ)

## Resource Naming

Resources are automatically named based on environment:

| Resource Type | Naming Pattern | Example |
|--------------|----------------|---------|
| S3 Storage | `{project}-{env}-storage` | `turtil-backend-development-storage` |
| S3 Logs | `{project}-{env}-logs` | `turtil-backend-development-logs` |
| ECR Repository | `{project}-{env}` | `turtil-backend-development` |
| RDS Instance | `{project}-{env}-db` | `turtil-backend-development-db` |

## Troubleshooting

### Common Issues

**1. Missing Environment Variables**
```bash
Error: No value for required variable
```
- Ensure all variables are in `.env`
- Run `source ./loadenv.sh` manually to check

**2. AWS Credentials**
```bash
Error: NoCredentialsError
```
- Check AWS CLI: `aws sts get-caller-identity`
- Verify AWS credentials in `.env`

**3. Terraform State Lock**
```bash
Error: Error acquiring the state lock
```
- Wait for other operations to complete
- Force unlock (dangerous): `terraform force-unlock LOCK_ID`

**4. Resource Already Exists**
```bash
Error: Resource already exists
```
- Import existing resource: `terraform import <resource> <id>`
- Or destroy and recreate

### Debug Mode

Enable verbose logging:
```bash
export TF_LOG=DEBUG
./local-plan.sh development
```

### State Management

View current state:
```bash
terraform state list
terraform state show <resource>
```

## Best Practices

### 1. Always Plan First
Never apply without planning:
```bash
./local-plan.sh development  # Review changes
./local-apply.sh development  # Apply if satisfied
```

### 2. Environment Isolation
- Use separate environments for different purposes
- Development for testing, production for live workloads
- Never mix environments

### 3. State Backup
Terraform state is stored locally for the `local` workspace:
```bash
# Backup state before major changes
cp terraform.tfstate terraform.tfstate.backup
```

### 4. Resource Cleanup
Regularly clean up unused resources:
```bash
# Review what will be destroyed
terraform plan -destroy -var-file=environments/development.tfvars

# Destroy if needed
./local-destroy.sh development
```

## CI/CD Integration

Local deployment complements GitHub Actions:

- **Local**: Development, testing, experimentation
- **GitHub Actions**: Production deployments, automated testing

Both use the same Terraform code but different execution environments.

## Security Notes

### 1. Environment Variables
- Never commit real secrets to git
- Use `.env` for local development only
- GitHub Actions uses encrypted secrets

### 2. AWS Permissions
- Use least-privilege IAM policies
- Regularly rotate AWS credentials
- Monitor AWS CloudTrail for unusual activity

### 3. State Files
- Local state files contain sensitive data
- Never commit `terraform.tfstate` to git
- Consider remote state for production

## Support

For issues with local deployment:

1. Check this documentation
2. Review Terraform logs with `TF_LOG=DEBUG`
3. Verify AWS permissions in `IAM_PERMISSIONS.md`
4. Check GitHub Issues for common problems

---

**⚠️ Important**: Local deployment is for development purposes. For production deployments, use the GitHub Actions workflows which include additional safety checks and monitoring.