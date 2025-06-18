#!/bin/bash
# ============================================================================
# TERRAFORM ENVIRONMENT VARIABLE LOADER
# ============================================================================
# 
# This script loads environment variables from .env file and exports them
# as Terraform variables (TF_VAR_*) for use with terraform commands
# 
# Usage:
#   source loadenv.sh
#   terraform plan
#   terraform apply
# 
# ============================================================================

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found in current directory"
    echo "Please create a .env file with your environment variables"
    return 1 2>/dev/null || exit 1
fi

echo "🔄 Loading environment variables from .env file..."

# Load environment variables from .env file
set -a
source .env
set +a

# Export application environment variables as Terraform variables
export TF_VAR_app_database_url="$DATABASE_URL"
export TF_VAR_app_secret_key="$SECRET_KEY"
export TF_VAR_app_algorithm="$ALGORITHM"
export TF_VAR_app_access_token_expire_minutes="$ACCESS_TOKEN_EXPIRE_MINUTES"
export TF_VAR_app_project_name="$PROJECT_NAME"
export TF_VAR_app_version="$VERSION"
export TF_VAR_app_environment="$ENVIRONMENT"
export TF_VAR_app_debug="$DEBUG"
export TF_VAR_app_log_level="$LOG_LEVEL"
export TF_VAR_app_cors_origins="$CORS_ORIGINS"
export TF_VAR_app_allowed_hosts="$ALLOWED_HOSTS"
export TF_VAR_app_rate_limit_calls="$RATE_LIMIT_CALLS"
export TF_VAR_app_rate_limit_period="$RATE_LIMIT_PERIOD"
export TF_VAR_app_otp_secret="$OTP_SECRET"
export TF_VAR_app_otp_expiry_minutes="$OTP_EXPIRY_MINUTES"
export TF_VAR_app_aws_access_key_id="$AWS_ACCESS_KEY_ID"
export TF_VAR_app_aws_secret_access_key="$AWS_SECRET_ACCESS_KEY"
export TF_VAR_app_aws_region="$AWS_REGION"  
export TF_VAR_app_aws_default_region="$AWS_DEFAULT_REGION"
export TF_VAR_app_s3_bucket_name="$S3_BUCKET_NAME"
export TF_VAR_app_upstash_redis_url="$UPSTASH_REDIS_URL"
export TF_VAR_app_upstash_redis_token="$UPSTASH_REDIS_TOKEN"
export TF_VAR_app_redis_user_cache_ttl="$REDIS_USER_CACHE_TTL"
export TF_VAR_app_redis_blacklist_ttl="$REDIS_BLACKLIST_TTL"
export TF_VAR_app_aws_ses_from_email="$AWS_SES_FROM_EMAIL"
export TF_VAR_app_aws_ses_region="$AWS_SES_REGION"
export TF_VAR_app_jwt_secret_key="$JWT_SECRET_KEY"
export TF_VAR_app_jwt_algorithm="$JWT_ALGORITHM"
export TF_VAR_app_jwt_expire_minutes="$JWT_EXPIRE_MINUTES"

echo "✅ Environment variables loaded and exported as Terraform variables"
echo ""
echo "Required variables status:"

# Check and display status of critical variables
check_var() {
    local var_name=$1
    local tf_var_name=$2
    local value=${!tf_var_name}
    
    if [ -n "$value" ]; then
        echo "  ✅ $var_name"
    else
        echo "  ❌ $var_name - MISSING"
    fi
}

check_var "DATABASE_URL" "TF_VAR_app_database_url"
check_var "SECRET_KEY" "TF_VAR_app_secret_key"
check_var "AWS_ACCESS_KEY_ID" "TF_VAR_app_aws_access_key_id"
check_var "AWS_SECRET_ACCESS_KEY" "TF_VAR_app_aws_secret_access_key"
check_var "S3_BUCKET_NAME" "TF_VAR_app_s3_bucket_name"
check_var "UPSTASH_REDIS_URL" "TF_VAR_app_upstash_redis_url"
check_var "UPSTASH_REDIS_TOKEN" "TF_VAR_app_upstash_redis_token"
check_var "OTP_SECRET" "TF_VAR_app_otp_secret"
check_var "JWT_SECRET_KEY" "TF_VAR_app_jwt_secret_key"
check_var "ENVIRONMENT" "TF_VAR_app_environment"
check_var "DEBUG" "TF_VAR_app_debug"

echo ""
echo "🚀 Ready to run Terraform commands!"
echo "   terraform plan"
echo "   terraform apply"