#!/bin/bash
# ============================================================================
# LOAD ENVIRONMENT VARIABLES FOR TERRAFORM
# ============================================================================
# This script loads environment variables from environment-specific .env files
# and exports them as TF_VAR_* variables for Terraform

set -e

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Determine environment from argument or default to 'dev'
ENVIRONMENT="${1:-dev}"

# Check for valid environment
case "$ENVIRONMENT" in
    "dev"|"test"|"prod")
        ;;
    *)
        echo "❌ Invalid environment: $ENVIRONMENT"
        echo "Valid environments: dev, test, prod"
        exit 1
        ;;
esac

# Check if environment-specific .env file exists
ENV_FILE="$PROJECT_ROOT/.env.$ENVIRONMENT"
if [[ ! -f "$ENV_FILE" ]]; then
    echo "❌ Environment file not found: $ENV_FILE"
    echo "Please create a .env.$ENVIRONMENT file in the project root directory"
    echo "You can use the populate-env.sh script to generate it from Terraform outputs"
    exit 1
fi

echo "📄 Loading environment variables for: $ENVIRONMENT"
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

# Environment-specific Terraform variables
case "$ENVIRONMENT" in
    "dev")
        export TF_VAR_enable_single_instance="true"
        export TF_VAR_enable_load_balancer="false"
        echo "🔧 Development mode: Single instance, no load balancer"
        ;;
    "test")
        export TF_VAR_enable_single_instance="false"
        export TF_VAR_enable_load_balancer="true"
        echo "🧪 Test mode: Auto scaling group with load balancer"
        ;;
    "prod")
        export TF_VAR_enable_single_instance="false"
        export TF_VAR_enable_load_balancer="true"
        echo "🚀 Production mode: Full auto scaling with load balancer and CloudFront"
        ;;
esac

echo "✅ Environment variables loaded for $ENVIRONMENT and exported as TF_VAR_* variables"
echo "💡 Use terraform workspace select $ENVIRONMENT before applying"