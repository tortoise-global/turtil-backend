#!/bin/bash
# ============================================================================
# POPULATE ENVIRONMENT FILES WITH TERRAFORM OUTPUTS
# ============================================================================
# This script populates .env files with actual values from Terraform deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TERRAFORM_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to get Terraform output
get_terraform_output() {
    local output_name="$1"
    local workspace="$2"
    
    cd "$TERRAFORM_DIR"
    
    # Select the correct workspace
    terraform workspace select "$workspace" >/dev/null 2>&1 || {
        print_error "Failed to select workspace: $workspace"
        return 1
    }
    
    # Get the output value
    terraform output -raw "$output_name" 2>/dev/null || {
        print_warning "Output '$output_name' not found in workspace '$workspace'"
        echo "TERRAFORM_OUTPUT_NOT_FOUND"
    }
}

# Function to populate environment file
populate_env_file() {
    local env_name="$1"
    local workspace="$2"
    
    print_info "Populating .env.$env_name with Terraform outputs..."
    
    local env_file="$PROJECT_ROOT/.env.$env_name"
    
    if [[ ! -f "$env_file" ]]; then
        print_error ".env.$env_name file not found!"
        return 1
    fi
    
    # Create backup
    cp "$env_file" "$env_file.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Get Terraform outputs
    print_info "Fetching database connection details..."
    local database_url
    database_url=$(get_terraform_output "application_environment_variables" "$workspace" | jq -r '.DATABASE_URL' 2>/dev/null || echo "TERRAFORM_OUTPUT_NOT_FOUND")
    
    print_info "Fetching S3 bucket information..."
    local s3_bucket_name
    s3_bucket_name=$(get_terraform_output "app_storage_bucket_name" "$workspace")
    
    print_info "Fetching deployment info..."
    local deployment_info
    deployment_info=$(get_terraform_output "deployment_info" "$workspace" 2>/dev/null || echo "{}")
    
    # Extract specific values
    local aws_region
    aws_region=$(echo "$deployment_info" | jq -r '.aws_region // "ap-south-1"' 2>/dev/null || echo "ap-south-1")
    
    local environment
    environment=$(echo "$deployment_info" | jq -r '.environment // "'$env_name'"' 2>/dev/null || echo "$env_name")
    
    # Create temporary file with replacements
    local temp_file=$(mktemp)
    
    # Copy original file to temp
    cp "$env_file" "$temp_file"
    
    # Replace placeholders
    if [[ "$database_url" != "TERRAFORM_OUTPUT_NOT_FOUND" && "$database_url" != "null" ]]; then
        print_success "Replacing DATABASE_URL..."
        sed -i.bak "s|DATABASE_URL=.*|DATABASE_URL=$database_url|g" "$temp_file"
    else
        print_warning "Database URL not available yet. Run terraform apply first."
    fi
    
    if [[ "$s3_bucket_name" != "TERRAFORM_OUTPUT_NOT_FOUND" && "$s3_bucket_name" != "null" ]]; then
        print_success "Replacing S3_BUCKET_NAME..."
        sed -i.bak "s|S3_BUCKET_NAME=.*|S3_BUCKET_NAME=$s3_bucket_name|g" "$temp_file"
    else
        print_warning "S3 bucket name not available yet. Run terraform apply first."
    fi
    
    # Update AWS region
    sed -i.bak "s|AWS_REGION=.*|AWS_REGION=$aws_region|g" "$temp_file"
    
    # Update environment name
    sed -i.bak "s|ENVIRONMENT=.*|ENVIRONMENT=$environment|g" "$temp_file"
    
    # Clean up sed backup files
    rm -f "$temp_file.bak"
    
    # Replace original file
    mv "$temp_file" "$env_file"
    
    print_success "Successfully populated .env.$env_name"
    
    # Show summary
    print_info "Environment file summary for $env_name:"
    echo "  📄 File: $env_file"
    echo "  🗄️  Database: ${database_url:0:50}..."
    echo "  🪣 S3 Bucket: $s3_bucket_name"
    echo "  🌍 AWS Region: $aws_region"
    echo ""
}

# Function to display usage
usage() {
    echo "Usage: $0 [ENVIRONMENT]"
    echo ""
    echo "ENVIRONMENT can be:"
    echo "  dev     - Populate .env.dev with dev resources"
    echo "  test    - Populate .env.test with test resources"
    echo "  prod    - Populate .env.prod with prod resources"
    echo "  local   - Show local Docker service info (.env.local already configured)"
    echo "  all     - Populate all environment files"
    echo ""
    echo "Examples:"
    echo "  $0 dev          # Populate dev environment"
    echo "  $0 prod         # Populate prod environment"
    echo "  $0 all          # Populate all environments"
    echo ""
}

# Function to check prerequisites
check_prerequisites() {
    # Check if we're in the right directory
    if [[ ! -f "$PROJECT_ROOT/.env.dev" ]]; then
        print_error "Environment files not found! Run this script from the project root."
        exit 1
    fi
    
    # Check if Terraform is available
    if ! command -v terraform &> /dev/null; then
        print_error "Terraform is not installed or not in PATH"
        exit 1
    fi
    
    # Check if jq is available
    if ! command -v jq &> /dev/null; then
        print_error "jq is not installed. Please install jq to parse JSON outputs."
        exit 1
    fi
    
    # Check if we're in a terraform directory
    if [[ ! -f "$TERRAFORM_DIR/main.tf" ]]; then
        print_error "Terraform configuration not found!"
        exit 1
    fi
}

# Main function
main() {
    local environment="$1"
    
    if [[ -z "$environment" ]]; then
        usage
        exit 1
    fi
    
    print_info "🚀 Starting environment file population..."
    print_info "Project Root: $PROJECT_ROOT"
    print_info "Terraform Dir: $TERRAFORM_DIR"
    echo ""
    
    check_prerequisites
    
    case "$environment" in
        "dev")
            populate_env_file "dev" "dev"
            ;;
        "test")
            populate_env_file "test" "test"
            ;;
        "prod")
            populate_env_file "prod" "prod"
            ;;
        "local")
            print_info "Local environment uses Docker services - no Terraform population needed"
            print_success ".env.local already configured with Docker service URLs:"
            echo "  🗄️  PostgreSQL: localhost:5432/turtil_db"
            echo "  🚀 Redis HTTP: localhost:8079"
            echo "  🪣 MinIO S3: localhost:9000/turtil-backend-local"
            echo "  📧 SES: support@turtil.co (same as all environments)"
            ;;
        "all")
            print_info "Populating all environment files..."
            populate_env_file "dev" "dev"
            populate_env_file "test" "test"
            populate_env_file "prod" "prod"
            print_info "Local environment uses Docker services - no Terraform population needed"
            ;;
        *)
            print_error "Invalid environment: $environment"
            usage
            exit 1
            ;;
    esac
    
    print_success "🎉 Environment file population completed!"
    print_info "💡 Remember to:"
    echo "  1. Review the updated .env files"
    echo "  2. Set actual AWS credentials"
    echo "  3. Configure Upstash Redis URLs manually"
    echo "  4. Update email configuration"
    echo "  5. Set proper SECRET_KEY values for prod"
}

# Run main function with all arguments
main "$@"