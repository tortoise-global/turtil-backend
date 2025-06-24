#!/bin/bash
# ============================================================================
# LOCAL TERRAFORM APPLY SCRIPT
# ============================================================================
# Applies Terraform changes for a specific environment locally

set -e

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

# Default to dev environment
ENVIRONMENT=${1:-dev}

# Validate environment
case "$ENVIRONMENT" in
    "dev"|"test"|"prod")
        ;;
    *)
        print_error "Invalid environment: $ENVIRONMENT"
        echo "Valid environments: dev, test, prod"
        exit 1
        ;;
esac

echo "🚀 Applying Terraform Changes for Local Development"
echo "==================================================="
print_info "Environment: $ENVIRONMENT"
print_info "Workspace: $ENVIRONMENT"
echo ""

# Load environment variables from environment-specific .env file
print_info "Loading environment variables from .env.$ENVIRONMENT..."
source ./scripts/loadenv.sh "$ENVIRONMENT"

# Switch to the correct workspace
CURRENT_WORKSPACE=$(terraform workspace show)
if [ "$CURRENT_WORKSPACE" != "$ENVIRONMENT" ]; then
    print_warning "Current workspace: $CURRENT_WORKSPACE"
    print_info "Switching to $ENVIRONMENT workspace..."
    terraform workspace select "$ENVIRONMENT" || terraform workspace new "$ENVIRONMENT"
fi

# Sync state with remote backend before applying
print_info "Syncing Terraform state with remote backend..."
terraform refresh -var-file="environments/$ENVIRONMENT.tfvars" || {
    print_warning "State refresh failed, continuing with apply..."
}

# Check if plan file exists
PLAN_FILE="tfplan-$ENVIRONMENT"
if [ ! -f "$PLAN_FILE" ]; then
    print_warning "No plan file found. Running plan first..."
    ./scripts/local-plan.sh "$ENVIRONMENT"
fi

print_info "Using plan file: $PLAN_FILE"
print_info "Using tfvars file: environments/$ENVIRONMENT.tfvars"
echo ""

# Show what will be applied
print_info "Terraform will apply the following plan:"
terraform show "$PLAN_FILE" | head -20
echo "..."
echo ""

# Confirmation prompt
read -p "🤔 Are you sure you want to apply these changes? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    print_error "Apply cancelled by user"
    exit 0
fi

# Run terraform apply
print_info "Running terraform apply for $ENVIRONMENT environment..."
terraform apply "$PLAN_FILE"

echo ""
print_success "Terraform apply completed successfully for $ENVIRONMENT!"
echo ""

# Show important outputs
print_info "Deployment Summary:"
case "$ENVIRONMENT" in
    "dev")
        echo "🔧 Development Environment Deployed"
        echo "   - Single EC2 instance (no load balancer)"
        echo "   - Cost optimized with spot instances"
        INSTANCE_INFO=$(terraform output -json dev_instance_info 2>/dev/null || echo "{}")
        if [ "$INSTANCE_INFO" != "{}" ]; then
            PUBLIC_IP=$(echo "$INSTANCE_INFO" | jq -r '.public_ip // "N/A"')
            echo "   - Public IP: $PUBLIC_IP"
            echo "   - Health URL: http://$PUBLIC_IP:8000/health"
            echo "   - App URL: http://$PUBLIC_IP:8000"
        fi
        ;;
    "test")
        echo "🧪 Test Environment Deployed"
        echo "   - Auto Scaling Group with Load Balancer"
        echo "   - Production-like testing setup"
        ALB_DNS=$(terraform output -raw example_alb_dns_name 2>/dev/null || echo "N/A")
        if [ "$ALB_DNS" != "N/A" ]; then
            echo "   - Load Balancer: http://$ALB_DNS"
            echo "   - Health URL: http://$ALB_DNS/health"
        fi
        ;;
    "prod")
        echo "🚀 Production Environment Deployed"
        echo "   - Full Auto Scaling with Load Balancer"
        echo "   - CloudFront CDN distribution"
        echo "   - Aurora Serverless v2 database"
        ALB_DNS=$(terraform output -raw example_alb_dns_name 2>/dev/null || echo "N/A")
        CF_DOMAIN=$(terraform output -json cloudfront_distribution 2>/dev/null | jq -r '.domain_name // "N/A"' || echo "N/A")
        if [ "$ALB_DNS" != "N/A" ]; then
            echo "   - Load Balancer: http://$ALB_DNS"
        fi
        if [ "$CF_DOMAIN" != "N/A" ]; then
            echo "   - CloudFront: https://$CF_DOMAIN"
        fi
        ;;
esac

echo ""
print_info "Next Steps:"
echo "1. 📊 Check all outputs: terraform output"
echo "2. 🗄️  Populate .env file: ./scripts/populate-env.sh $ENVIRONMENT"
echo "3. 🔍 Verify deployment health"
echo "4. 🐳 Deploy application containers"

# Clean up plan file
print_info "Cleaning up plan file..."
rm -f "$PLAN_FILE"
print_success "Plan file cleaned up"

# Suggest running populate-env script
echo ""
print_warning "Don't forget to run the populate-env script to update your .env.$ENVIRONMENT file with actual database URLs and resource names:"
echo "  ./scripts/populate-env.sh $ENVIRONMENT"