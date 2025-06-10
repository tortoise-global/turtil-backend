# Terraform Infrastructure for Turtil Backend

This directory contains Terraform configurations to set up AWS infrastructure for the Turtil Backend application.

## What This Creates

- **S3 Bucket**: For file uploads with proper security, versioning, and lifecycle policies
- **IAM User**: With minimal permissions for S3 access
- **Security Features**: 
  - Server-side encryption
  - Public access blocked
  - CORS configuration
  - Lifecycle policies for cost optimization

## Prerequisites

1. **AWS CLI configured** with appropriate credentials
2. **Terraform installed** (>= 1.0)
3. **AWS account** with permissions to create S3 buckets and IAM resources

## Quick Start

1. **Copy the example variables file:**
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. **Edit terraform.tfvars:**
   ```bash
   # Update the s3_bucket_name to something globally unique
   s3_bucket_name = "turtil-uploads-yourname-dev"
   
   # Update other variables as needed
   aws_region = "us-east-1"
   environment = "development"
   ```

3. **Initialize Terraform:**
   ```bash
   terraform init
   ```

4. **Plan the deployment:**
   ```bash
   terraform plan
   ```

5. **Apply the configuration:**
   ```bash
   terraform apply
   ```

6. **Get the output values:**
   ```bash
   # Get all outputs
   terraform output
   
   # Get specific values for your .env file
   terraform output -json env_variables
   ```

## Updating Your .env File

After running `terraform apply`, update your backend's `.env` file with the output values:

```bash
# Get the secret values (sensitive output)
terraform output -raw iam_secret_access_key

# Update your .env file with:
AWS_ACCESS_KEY_ID=<from terraform output>
AWS_SECRET_ACCESS_KEY=<from terraform output>
AWS_REGION=<from terraform output>
S3_BUCKET_NAME=<from terraform output>
```

## File Structure

- `main.tf` - Main infrastructure resources
- `variables.tf` - Input variables
- `outputs.tf` - Output values
- `terraform.tfvars.example` - Example variables file
- `README.md` - This file

## Security Notes

- The S3 bucket is configured with public access blocked
- IAM user has minimal permissions (only S3 access)
- Server-side encryption is enabled
- Access keys are marked as sensitive in outputs

## Cost Optimization

- Lifecycle policies transition files to cheaper storage after 30 days
- Files are automatically deleted after 365 days
- Incomplete multipart uploads are cleaned up after 1 day

## Future Enhancements

This configuration is designed to be extended with:
- CloudFront CDN distribution
- Lambda functions for image processing
- CloudWatch monitoring
- Additional security features

## Cleanup

To destroy all resources:
```bash
terraform destroy
```

**Warning**: This will permanently delete the S3 bucket and all files in it!