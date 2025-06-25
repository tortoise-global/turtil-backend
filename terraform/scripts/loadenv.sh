#!/bin/bash
# ============================================================================
# LOAD ENVIRONMENT VARIABLES FOR TERRAFORM
# ============================================================================
# This script loads environment variables from environment-specific .env files
# and exports them as TF_VAR_* variables for Terraform

set -e

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Always use dev environment
ENVIRONMENT="dev"

# Check if environment file exists
ENV_FILE="$PROJECT_ROOT/.env.dev"
if [[ ! -f "$ENV_FILE" ]]; then
    echo "❌ Environment file not found: $ENV_FILE"
    echo "Please create a .env.dev file in the project root directory"
    exit 1
fi

echo "📄 Loading environment variables for dev"
echo "📄 From file: $ENV_FILE"

# Source the environment-specific .env file
set -a  # Automatically export all variables
source "$ENV_FILE"
set +a  # Stop automatically exporting

# Export Terraform variables with environment-specific values
export TF_VAR_app_database_url="$DATABASE_URL"
export TF_VAR_app_secret_key="$SECRET_KEY"
export TF_VAR_app_algorithm="$ALGORITHM"
export TF_VAR_app_access_token_expire_minutes="$ACCESS_TOKEN_EXPIRE_MINUTES"
export TF_VAR_app_project_name="$PROJECT_NAME"
export TF_VAR_app_version="$VERSION"
export TF_VAR_app_log_level="$LOG_LEVEL"
export TF_VAR_app_rate_limit_calls="$RATE_LIMIT_CALLS"
export TF_VAR_app_rate_limit_period="$RATE_LIMIT_PERIOD"
export TF_VAR_app_otp_expiry_minutes="$OTP_EXPIRY_MINUTES"
export TF_VAR_app_otp_max_attempts="$OTP_MAX_ATTEMPTS"
export TF_VAR_app_dev_otp="$DEV_OTP"
export TF_VAR_app_cors_origins="$CORS_ORIGINS"
export TF_VAR_app_allowed_hosts="$ALLOWED_HOSTS"
export TF_VAR_app_refresh_token_expire_minutes="$REFRESH_TOKEN_EXPIRE_MINUTES"
export TF_VAR_app_redis_user_cache_ttl="$REDIS_USER_CACHE_TTL"
export TF_VAR_app_redis_blacklist_ttl="$REDIS_BLACKLIST_TTL"
export TF_VAR_app_db_username="$DB_USERNAME"
export TF_VAR_app_db_password="$DB_PASSWORD"
export TF_VAR_app_aws_access_key_id="$AWS_ACCESS_KEY_ID"
export TF_VAR_app_aws_secret_access_key="$AWS_SECRET_ACCESS_KEY"
export TF_VAR_project_name="$PROJECT_NAME"
export TF_VAR_app_upstash_redis_url="$UPSTASH_REDIS_URL"
export TF_VAR_app_upstash_redis_token="$UPSTASH_REDIS_TOKEN"
export TF_VAR_app_aws_ses_from_email="$AWS_SES_FROM_EMAIL"
export TF_VAR_app_aws_ses_region="$AWS_SES_REGION"
export TF_VAR_ecr_account_id="$ECR_ACCOUNT_ID"
export TF_VAR_environment="$ENVIRONMENT"
export TF_VAR_app_debug="$DEBUG"
export TF_VAR_aws_region="$AWS_REGION"
export TF_VAR_custom_ami_id="$CUSTOM_AMI_ID"
export TF_VAR_app_s3_bucket_name="$S3_BUCKET_NAME"

echo "✅ Environment variables loaded for dev and exported as TF_VAR_* variables"
echo "🔧 You can now run terraform commands like: terraform plan, terraform apply"