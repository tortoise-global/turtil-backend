#!/bin/bash

# Get Deployed Resources Script
# This script shows you all the deployed resources and their details

set -e

echo "📊 Getting deployed resource information..."
echo ""

# Check if we're in the terraform-files directory
if [ ! -f "main.tf" ]; then
    echo "❌ Error: Please run this script from the terraform-files directory"
    exit 1
fi

# Load environment variables from current directory
if [ -f "../.env" ]; then
    export $(grep -v '^#' ../.env | xargs)
elif [ -f "../.env.dev" ]; then
    export $(grep -v '^#' ../.env.dev | xargs)
fi

# Set Terraform variables
export TF_VAR_aws_region="$AWS_REGION"
export TF_VAR_secret_key="$SECRET_KEY"
export TF_VAR_aws_access_key_id="$AWS_ACCESS_KEY_ID"
export TF_VAR_aws_secret_access_key="$AWS_SECRET_ACCESS_KEY"
export TF_VAR_upstash_redis_url="$UPSTASH_REDIS_URL"
export TF_VAR_upstash_redis_token="$UPSTASH_REDIS_TOKEN"
export TF_VAR_aws_ses_from_email="$AWS_SES_FROM_EMAIL"

echo "🌐 Application Load Balancer:"
ALB_DNS=$(terraform output -raw alb_dns_name 2>/dev/null || echo "Not available")
echo "   URL: http://$ALB_DNS"
echo "   Health: http://$ALB_DNS/health"
echo ""

echo "🐳 Docker Registry (ECR):"
ECR_URL=$(terraform output -raw ecr_repository_url 2>/dev/null || echo "Not available")
echo "   Repository: $ECR_URL"
echo ""

echo "💾 Database:"
DB_URL=$(terraform output -raw database_url 2>/dev/null || echo "Sensitive - not shown")
echo "   Connection: $DB_URL"
echo ""

echo "📦 S3 Storage:"
S3_BUCKET=$(terraform output -raw s3_bucket_name 2>/dev/null || echo "Not available")
echo "   Bucket: $S3_BUCKET"
echo ""

echo "🖥️  Auto Scaling Group:"
ASG_NAME=$(terraform output -raw asg_name 2>/dev/null || echo "Not available")
echo "   ASG Name: $ASG_NAME"
echo ""

echo "🏗️  Infrastructure:"
AMI_ID=$(terraform output -raw custom_ami_id 2>/dev/null || echo "Not available")
VPC_ID=$(terraform output -raw vpc_id 2>/dev/null || echo "Not available")
echo "   AMI ID: $AMI_ID"
echo "   VPC ID: $VPC_ID"
echo "   Region: $AWS_REGION"
echo ""

echo "📋 All Terraform Outputs:"
terraform output

echo ""
echo "💡 Useful commands:"
echo "   • Test health: curl http://$ALB_DNS/health"
echo "   • Login to ECR: aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URL"
echo "   • View ASG instances: aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names $ASG_NAME --region $AWS_REGION"