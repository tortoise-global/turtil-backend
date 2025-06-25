# Turtil Backend Infrastructure

This directory contains the Terraform configuration for the Turtil Backend infrastructure on AWS.

## Architecture

The infrastructure is organized into reusable modules:

```
terraform/
├── main.tf                    # Main configuration using modules
├── variables-modular.tf       # Input variables
├── main-legacy.tf            # Original monolithic configuration (backup)
├── user_data.sh              # EC2 initialization script
└── modules/                  # Reusable infrastructure modules
    ├── vpc/                  # Virtual Private Cloud and networking
    ├── rds/                  # PostgreSQL database
    ├── ec2/                  # Compute instances
    ├── ecr/                  # Container registry
    ├── s3/                   # Storage buckets
    └── iam/                  # Identity and access management
```

## Modules Overview

### VPC Module (`modules/vpc/`)
- **Purpose**: Creates isolated network infrastructure
- **Resources**: VPC, subnets, security groups, internet gateway, route tables
- **Features**: 
  - Public and private subnets across multiple AZs
  - Configurable security groups for EC2 and RDS
  - Optional external database access for development

### RDS Module (`modules/rds/`)
- **Purpose**: Managed PostgreSQL database
- **Resources**: RDS instance, parameter groups, subnet groups
- **Features**:
  - Configurable instance class and storage
  - Automated backups and maintenance windows
  - Performance Insights and monitoring options
  - Encryption at rest

### ECR Module (`modules/ecr/`)
- **Purpose**: Docker container registry
- **Resources**: ECR repository, lifecycle policies
- **Features**:
  - Image scanning and vulnerability assessment
  - Lifecycle policies for image cleanup
  - Cross-account access policies

### S3 Module (`modules/s3/`)
- **Purpose**: Object storage for application files
- **Resources**: S3 buckets with configurations
- **Features**:
  - Versioning and lifecycle management
  - Server-side encryption
  - CORS configuration for file uploads
  - Public access blocking

### IAM Module (`modules/iam/`)
- **Purpose**: Identity and access management
- **Resources**: IAM roles, policies, instance profiles
- **Features**:
  - EC2 service role with minimal permissions
  - ECR, S3, and SES access policies
  - CloudWatch Logs integration

### EC2 Module (`modules/ec2/`)
- **Purpose**: Application compute instances
- **Resources**: EC2 instances, EBS volumes, CloudWatch alarms
- **Features**:
  - Configurable instance types and storage
  - User data for application setup
  - Optional Elastic IP and monitoring
  - Security best practices

## Usage

### Prerequisites

1. **AWS CLI configured** with appropriate credentials
2. **Terraform installed** (version >= 1.5.0)
3. **S3 bucket** for Terraform state storage
4. **Route53 hosted zone** for domain management

### Deployment

1. **Initialize Terraform**:
   ```bash
   terraform init
   ```

2. **Review the plan**:
   ```bash
   terraform plan
   ```

3. **Apply the configuration**:
   ```bash
   terraform apply
   ```

### Environment Variables

Set the following variables either via `.tfvars` file or environment variables:

```bash
# Security
export TF_VAR_app_secret_key="your-jwt-secret-key"
export TF_VAR_app_upstash_redis_url="https://your-redis-url"
export TF_VAR_app_upstash_redis_token="your-redis-token"

# AWS Credentials
export TF_VAR_app_aws_access_key_id="your-aws-access-key"
export TF_VAR_app_aws_secret_access_key="your-aws-secret-key"

# Optional: Custom AMI
export TF_VAR_custom_ami_id="ami-xxxxxxxxx"
```

### State Management

The Terraform state is stored in S3 with the following configuration:

```hcl
backend "s3" {
  bucket = "turtil-backend-terraform"
  key    = "modular-dev/terraform.tfstate"
  region = "ap-south-1"
}
```

## Module Configuration

### Development Environment

For development, the infrastructure includes:
- Public database access for external connections
- Single AZ deployment for cost optimization
- Minimal monitoring and alerting
- Mutable ECR image tags

### Production Considerations

For production deployment, consider:
- Private database subnets only
- Multi-AZ RDS deployment
- Enhanced monitoring and alerting
- Immutable ECR image tags
- WAF and CloudFront integration

## Customization

### Adding New Modules

1. Create module directory: `mkdir modules/new-module`
2. Create `main.tf`, `variables.tf`, `outputs.tf`
3. Reference in main configuration:
   ```hcl
   module "new_module" {
     source = "./modules/new-module"
     # variables...
   }
   ```

### Modifying Existing Modules

Each module is self-contained and can be modified independently:
- Update variables in `variables.tf`
- Modify resources in `main.tf`
- Adjust outputs in `outputs.tf`

## Security Best Practices

- **Least Privilege**: IAM roles have minimal required permissions
- **Encryption**: EBS volumes and S3 buckets encrypted by default
- **Network Isolation**: Private subnets for sensitive resources
- **Security Groups**: Restrictive ingress rules
- **Secrets Management**: Sensitive variables marked as sensitive

## Troubleshooting

### Common Issues

1. **State Lock**: If Terraform state is locked, check for stuck processes
2. **Resource Conflicts**: Use `terraform import` for existing resources
3. **Permission Errors**: Verify AWS credentials and IAM permissions
4. **Module Dependencies**: Ensure proper dependency ordering

### Validation

```bash
# Validate configuration
terraform validate

# Format code
terraform fmt -recursive

# Security scan (if tfsec installed)
tfsec .
```

## Migration from Legacy

The original monolithic configuration is preserved as `main-legacy.tf`. To migrate:

1. **Export existing state**: `terraform state pull > legacy-state.json`
2. **Import resources**: Use module import commands
3. **Verify plan**: Ensure no unintended changes
4. **Apply gradually**: Apply modules one at a time

## Outputs

The configuration provides comprehensive outputs:

- **Infrastructure Info**: Complete resource details
- **Application URLs**: API endpoints and documentation
- **Resource Identifiers**: For integration with other systems
- **Legacy Compatibility**: Maintains existing output format

## Support

For issues or questions:
1. Check Terraform documentation
2. Review AWS service documentation
3. Validate with `terraform plan`
4. Check CloudTrail for API errors