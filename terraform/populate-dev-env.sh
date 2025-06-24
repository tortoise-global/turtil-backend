#!/bin/bash
# ============================================================================
# POPULATE DEV ENVIRONMENT FILE WITH TERRAFORM OUTPUTS
# ============================================================================

set -e

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env.dev"

echo "🔄 Populating .env.dev with Terraform outputs..."

# Check if .env.dev exists
if [[ ! -f "$ENV_FILE" ]]; then
    echo "❌ .env.dev file not found at $ENV_FILE"
    exit 1
fi

# Get Terraform outputs
echo "📊 Getting Terraform outputs..."
DATABASE_ENDPOINT=$(terraform output -raw database_endpoint 2>/dev/null || echo "")
S3_BUCKET=$(terraform output -raw s3_bucket_name 2>/dev/null || echo "")
ECR_URL=$(terraform output -raw ecr_repository_url 2>/dev/null || echo "")

# Check if database is ready
if [[ -z "$DATABASE_ENDPOINT" ]]; then
    echo "⏳ Database is still being created. Checking status..."
    terraform refresh
    DATABASE_ENDPOINT=$(terraform output -raw database_endpoint 2>/dev/null || echo "")
    
    if [[ -z "$DATABASE_ENDPOINT" ]]; then
        echo "❌ Database not ready yet. Please wait and run this script again."
        echo "💡 You can check progress with: terraform show"
        exit 1
    fi
fi

# Extract just the endpoint without port (RDS includes :5432)
DATABASE_HOST=$(echo "$DATABASE_ENDPOINT" | cut -d: -f1)

# Construct the database URL
DATABASE_URL="postgresql+asyncpg://turtiluser:DevPassword123!@${DATABASE_HOST}:5432/turtil_backend_dev"

echo "✅ Terraform outputs retrieved:"
echo "   Database: $DATABASE_HOST"
echo "   S3 Bucket: $S3_BUCKET"
echo "   ECR URL: $ECR_URL"

# Update .env.dev file
echo "📝 Updating .env.dev file..."

# Backup original file
cp "$ENV_FILE" "$ENV_FILE.backup"

# Update DATABASE_URL
sed -i.tmp "s|DATABASE_URL=.*|DATABASE_URL=$DATABASE_URL|g" "$ENV_FILE"

# Update S3_BUCKET_NAME
sed -i.tmp "s|S3_BUCKET_NAME=.*|S3_BUCKET_NAME=$S3_BUCKET|g" "$ENV_FILE"

# Remove temporary file created by sed
rm -f "$ENV_FILE.tmp"

echo "✅ .env.dev updated successfully!"
echo "📋 Updated values:"
echo "   DATABASE_URL: $DATABASE_URL"
echo "   S3_BUCKET_NAME: $S3_BUCKET"
echo ""
echo "🚀 Dev environment is ready! You can now:"
echo "   1. cd /Users/lohit/Desktop/code/turtil-backend"
echo "   2. export ENV_FILE=.env.dev"
echo "   3. source venv/bin/activate"
echo "   4. python run.py"
echo ""
echo "💡 Backup created at: $ENV_FILE.backup"