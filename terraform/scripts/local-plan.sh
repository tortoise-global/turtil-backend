#!/bin/bash
# ============================================================================
# LOCAL TERRAFORM PLAN SCRIPT
# ============================================================================
# Creates Terraform execution plan for a specific environment locally

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

echo "🔍 Planning Terraform Changes for Local Development"
echo "=================================================="
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

# Determine which tfvars file to use
TFVARS_FILE="environments/${ENVIRONMENT}.tfvars"

if [ ! -f "$TFVARS_FILE" ]; then
    print_error "$TFVARS_FILE not found!"
    echo "Available environments:"
    ls -1 environments/*.tfvars 2>/dev/null | sed 's/environments\///g' | sed 's/\.tfvars//g' || echo "No environment files found"
    exit 1
fi

print_info "Using variables file: $TFVARS_FILE"
print_info "Workspace: $ENVIRONMENT"
echo ""

# Show environment-specific configuration
case "$ENVIRONMENT" in
    "dev")
        print_info "Development Configuration:"
        echo "  ✅ Single EC2 instance (no load balancer)"
        echo "  ✅ Spot instances for cost savings"
        echo "  ✅ RDS t4g.micro single-AZ"
        echo "  ✅ Estimated cost: ~$15-20/month"
        ;;
    "test")
        print_info "Test Configuration:"
        echo "  ✅ Auto Scaling Group with Load Balancer"
        echo "  ✅ Production-like testing setup"
        echo "  ✅ RDS t4g.micro"
        echo "  ✅ Estimated cost: ~$30-35/month"
        ;;
    "prod")
        print_info "Production Configuration:"
        echo "  ✅ Auto Scaling Group with Load Balancer"
        echo "  ✅ CloudFront CDN distribution"
        echo "  ✅ Aurora Serverless v2"
        echo "  ✅ High availability setup"
        echo "  ✅ Estimated cost: ~$60-80/month"
        ;;
esac
echo ""

# Run terraform plan
PLAN_FILE="tfplan-$ENVIRONMENT"
print_info "Running terraform plan..."
terraform plan -var-file="$TFVARS_FILE" -out="$PLAN_FILE"

echo ""
print_success "Terraform plan completed successfully!"
echo ""
print_info "Plan Summary:"
echo "  📋 Plan saved as: $PLAN_FILE"
echo "  📁 Variables from: $TFVARS_FILE"
echo "  🏗️  Workspace: $ENVIRONMENT"
echo ""
print_info "Next Steps:"
echo "1. Review the plan above"
echo "2. Apply changes: ./scripts/local-apply.sh $ENVIRONMENT"
echo "3. Or destroy: ./scripts/local-destroy.sh $ENVIRONMENT"
echo ""

# Show plan summary
PLAN_SUMMARY=$(terraform show -no-color "$PLAN_FILE" | grep -E "Plan:|No changes" | head -1)
if [ -n "$PLAN_SUMMARY" ]; then
    print_info "Plan Summary: $PLAN_SUMMARY"
fi