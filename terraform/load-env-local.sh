#!/bin/bash
# ============================================================================
# LOAD TERRAFORM ENVIRONMENT FOR LOCAL DEVELOPMENT
# ============================================================================
# This script loads environment variables into your current terminal session
# for local terraform operations. 
#
# Usage:
#   source ./load-env-local.sh
#   # or
#   . ./load-env-local.sh
#
# After sourcing, you can run terraform commands directly:
#   terraform plan
#   terraform apply
#   terraform destroy
#
# To unload the environment variables, run:
#   unset $(grep -v '^#' ../.env.dev | grep '=' | cut -d'=' -f1 | xargs)
#
# ============================================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# Check if script is being sourced (not executed)
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    print_error "This script must be sourced, not executed!"
    echo "Usage: source ./load-env-local.sh"
    echo "   or: . ./load-env-local.sh"
    exit 1
fi

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

print_info "Loading Terraform environment variables for local development..."
print_info "Project root: $PROJECT_ROOT"

# Check if .env.dev file exists
ENV_FILE="$PROJECT_ROOT/.env.dev"
if [[ ! -f "$ENV_FILE" ]]; then
    print_error "Environment file not found: $ENV_FILE"
    print_warning "Please create a .env.dev file in the project root directory"
    return 1
fi

print_info "Loading from: $ENV_FILE"

# Load environment variables from .env.dev
set -a  # Automatically export all variables
source "$ENV_FILE"
set +a  # Stop automatically exporting

# Export Terraform variables with TF_VAR_ prefix
export TF_VAR_app_project_name="$PROJECT_NAME"
export TF_VAR_app_version="$VERSION"
export TF_VAR_app_environment="dev"
export TF_VAR_app_debug="$DEBUG"
export TF_VAR_app_log_level="$LOG_LEVEL"

# Security & Authentication
export TF_VAR_app_secret_key="$SECRET_KEY"
export TF_VAR_app_algorithm="$ALGORITHM"
export TF_VAR_app_access_token_expire_minutes="$ACCESS_TOKEN_EXPIRE_MINUTES"
export TF_VAR_app_refresh_token_expire_minutes="$REFRESH_TOKEN_EXPIRE_MINUTES"

# OTP Configuration
export TF_VAR_app_otp_expiry_minutes="$OTP_EXPIRY_MINUTES"
export TF_VAR_app_otp_max_attempts="$OTP_MAX_ATTEMPTS"
export TF_VAR_app_dev_otp="$DEV_OTP"

# Application Settings
export TF_VAR_app_cors_origins="$CORS_ORIGINS"
export TF_VAR_app_allowed_hosts="$ALLOWED_HOSTS"
export TF_VAR_app_rate_limit_calls="$RATE_LIMIT_CALLS"
export TF_VAR_app_rate_limit_period="$RATE_LIMIT_PERIOD"

# Database & Cache
export TF_VAR_app_db_username="$DB_USERNAME"
export TF_VAR_app_db_password="$DB_PASSWORD"
export TF_VAR_app_database_url="$DATABASE_URL"
export TF_VAR_app_upstash_redis_url="$UPSTASH_REDIS_URL"
export TF_VAR_app_upstash_redis_token="$UPSTASH_REDIS_TOKEN"
export TF_VAR_app_redis_user_cache_ttl="$REDIS_USER_CACHE_TTL"
export TF_VAR_app_redis_blacklist_ttl="$REDIS_BLACKLIST_TTL"

# AWS Services
export TF_VAR_app_aws_access_key_id="$AWS_ACCESS_KEY_ID"
export TF_VAR_app_aws_secret_access_key="$AWS_SECRET_ACCESS_KEY"
export TF_VAR_app_aws_region="$AWS_REGION"
export TF_VAR_app_aws_ses_from_email="$AWS_SES_FROM_EMAIL"
export TF_VAR_app_aws_ses_region="$AWS_SES_REGION"
export TF_VAR_ecr_account_id="$ECR_ACCOUNT_ID"
export TF_VAR_app_s3_bucket_name="$S3_BUCKET_NAME"
export TF_VAR_custom_ami_id="$CUSTOM_AMI_ID"

# Legacy compatibility
export TF_VAR_project_name="$PROJECT_NAME"
export TF_VAR_aws_region="$AWS_REGION"

print_success "Environment variables loaded successfully!"
echo ""
print_info "Available Terraform commands:"
echo "  🔍 terraform plan          - See what changes will be made"
echo "  🚀 terraform apply         - Apply changes to AWS"
echo "  🗑️  terraform destroy       - Remove all AWS resources"
echo "  📊 terraform output        - Show output values"
echo "  🔧 terraform refresh       - Sync state with real resources"
echo ""
print_warning "Current environment: dev"
print_warning "This will affect your AWS account: $AWS_ACCESS_KEY_ID"
echo ""
print_info "To unload environment variables, run:"
echo "  unset \$(grep -v '^#' $PROJECT_ROOT/.env.dev | grep '=' | cut -d'=' -f1 | xargs)"