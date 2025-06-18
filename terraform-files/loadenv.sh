#!/bin/bash

# Script to set Terraform variables from local .env file
# Usage: source ./loadenv.sh

# Check if .env file exists in parent directory
if [ ! -f "../.env" ]; then
    echo "Error: .env file not found in parent directory"
    exit 1
fi

echo "Setting Terraform variables from .env file..."

# Source the .env file to load variables
set -a  # automatically export all variables
source ../.env
set +a  # stop automatically exporting

# Export Terraform variables with TF_VAR_ prefix
export TF_VAR_app_database_url="$DATABASE_URL"
export TF_VAR_app_secret_key="$SECRET_KEY"
export TF_VAR_app_algorithm="$ALGORITHM"
export TF_VAR_app_access_token_expire_minutes="$ACCESS_TOKEN_EXPIRE_MINUTES"
export TF_VAR_app_project_name="$PROJECT_NAME"
export TF_VAR_app_version="$VERSION"
export TF_VAR_app_environment="$ENVIRONMENT"
export TF_VAR_app_debug="$DEBUG"
export TF_VAR_app_log_level="$LOG_LEVEL"
export TF_VAR_app_rate_limit_calls="$RATE_LIMIT_CALLS"
export TF_VAR_app_rate_limit_period="$RATE_LIMIT_PERIOD"
export TF_VAR_app_otp_secret="$OTP_SECRET"
export TF_VAR_app_otp_expiry_minutes="$OTP_EXPIRY_MINUTES"
export TF_VAR_app_aws_access_key_id="$AWS_ACCESS_KEY_ID"
export TF_VAR_app_aws_secret_access_key="$AWS_SECRET_ACCESS_KEY"
export TF_VAR_app_aws_region="$AWS_REGION"
export TF_VAR_app_s3_bucket_name="$S3_BUCKET_NAME"
export TF_VAR_app_upstash_redis_url="$UPSTASH_REDIS_URL"
export TF_VAR_app_upstash_redis_token="$UPSTASH_REDIS_TOKEN"
export TF_VAR_app_redis_user_cache_ttl="$REDIS_USER_CACHE_TTL"
export TF_VAR_app_redis_blacklist_ttl="$REDIS_BLACKLIST_TTL"

echo "✅ Terraform variables exported successfully!"
echo ""
echo "Now you can run Terraform commands without being prompted for variables:"
echo "  terraform plan"
echo "  terraform apply"
echo ""
echo "Available TF variables:"
echo "  TF_VAR_app_database_url"
echo "  TF_VAR_app_secret_key"
echo "  TF_VAR_app_algorithm"
echo "  TF_VAR_app_access_token_expire_minutes"
echo "  TF_VAR_app_project_name"
echo "  TF_VAR_app_version"
echo "  TF_VAR_app_environment"
echo "  TF_VAR_app_debug"
echo "  TF_VAR_app_log_level"
echo "  TF_VAR_app_rate_limit_calls"
echo "  TF_VAR_app_rate_limit_period"
echo "  TF_VAR_app_otp_secret"
echo "  TF_VAR_app_otp_expiry_minutes"
echo "  TF_VAR_app_aws_access_key_id"
echo "  TF_VAR_app_aws_secret_access_key"
echo "  TF_VAR_app_aws_region"
echo "  TF_VAR_app_s3_bucket_name"
echo "  TF_VAR_app_upstash_redis_url"
echo "  TF_VAR_app_upstash_redis_token"
echo "  TF_VAR_app_redis_user_cache_ttl"
echo "  TF_VAR_app_redis_blacklist_ttl"
