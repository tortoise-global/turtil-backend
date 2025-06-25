#!/bin/bash

# Terraform State Sync Script
# This script syncs your local Terraform state with the deployed infrastructure

set -e

echo "🔄 Syncing local Terraform state with deployed infrastructure..."
echo ""

# Load environment variables from current directory
if [ -f "../.env" ]; then
    echo "📁 Loading environment variables from .env..."
    export $(grep -v '^#' ../.env | xargs)
elif [ -f "../.env.dev" ]; then
    echo "📁 Loading environment variables from .env.dev..."
    export $(grep -v '^#' ../.env.dev | xargs)
else
    echo "❌ Error: .env or .env.dev file not found. Please create it with your AWS credentials."
    exit 1
fi

# Check if we're in the terraform-files directory
if [ ! -f "main.tf" ]; then
    echo "❌ Error: Please run this script from the terraform-files directory"
    exit 1
fi

echo "🌍 AWS Region: $AWS_REGION"
echo "🏗️  Environment: dev"
echo ""

# Set Terraform variables from environment
export TF_VAR_aws_region="$AWS_REGION"
export TF_VAR_secret_key="$SECRET_KEY"
export TF_VAR_aws_access_key_id="$AWS_ACCESS_KEY_ID"
export TF_VAR_aws_secret_access_key="$AWS_SECRET_ACCESS_KEY"
export TF_VAR_upstash_redis_url="$UPSTASH_REDIS_URL"
export TF_VAR_upstash_redis_token="$UPSTASH_REDIS_TOKEN"
export TF_VAR_aws_ses_from_email="$AWS_SES_FROM_EMAIL"

echo "🔧 Initializing Terraform backend..."
terraform init

echo ""
echo "📥 Refreshing Terraform state from AWS..."
terraform refresh

echo ""
echo "📋 Terraform state synced successfully!"
echo ""
echo "🎯 Current infrastructure status:"
terraform output

echo ""
echo "✅ Local Terraform state is now synced with deployed infrastructure"
echo ""
echo "💡 Next steps:"
echo "   • Run 'terraform plan' to see any differences"
echo "   • Run 'terraform apply' to apply any changes"
echo "   • Use 'terraform output' to get resource information"