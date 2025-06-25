#!/bin/bash
# ============================================================================
# TERRAFORM LOCAL OPERATIONS HELPER
# ============================================================================
# This script provides convenient terraform operations for local development
# It automatically loads environment variables and provides common commands
#
# Usage:
#   ./tf-local.sh plan     - Run terraform plan
#   ./tf-local.sh apply    - Run terraform apply
#   ./tf-local.sh destroy  - Run terraform destroy
#   ./tf-local.sh output   - Show terraform outputs
#   ./tf-local.sh init     - Initialize terraform
#   ./tf-local.sh refresh  - Refresh terraform state
#   ./tf-local.sh shell    - Open a shell with environment loaded
#
# ============================================================================

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

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load environment variables
print_info "Loading environment variables..."
source "$SCRIPT_DIR/scripts/loadenv.sh"

# Function to show usage
show_usage() {
    echo "Usage: $0 <command>"
    echo ""
    echo "Available commands:"
    echo "  plan     - Run terraform plan"
    echo "  apply    - Run terraform apply with confirmation"
    echo "  destroy  - Run terraform destroy with confirmation"
    echo "  output   - Show terraform outputs"
    echo "  init     - Initialize terraform"
    echo "  refresh  - Refresh terraform state"
    echo "  shell    - Open a shell with environment loaded"
    echo ""
    echo "Examples:"
    echo "  $0 plan"
    echo "  $0 apply"
    echo "  $0 output"
}

# Check if command is provided
if [ $# -eq 0 ]; then
    print_error "No command provided"
    show_usage
    exit 1
fi

COMMAND="$1"

case "$COMMAND" in
    "plan")
        print_info "Running terraform plan..."
        terraform plan
        ;;
    "apply")
        print_warning "This will apply changes to your AWS account!"
        echo "AWS Account: $AWS_ACCESS_KEY_ID"
        echo "Environment: dev"
        echo ""
        read -p "🤔 Are you sure you want to apply these changes? (yes/no): " CONFIRM
        if [ "$CONFIRM" = "yes" ]; then
            print_info "Running terraform apply..."
            terraform apply
        else
            print_error "Apply cancelled by user"
            exit 0
        fi
        ;;
    "destroy")
        print_warning "This will DESTROY all resources in your AWS account!"
        echo "AWS Account: $AWS_ACCESS_KEY_ID"
        echo "Environment: dev"
        echo ""
        read -p "🚨 Are you ABSOLUTELY sure you want to destroy all resources? (yes/no): " CONFIRM
        if [ "$CONFIRM" = "yes" ]; then
            read -p "🚨 This cannot be undone. Type 'destroy' to confirm: " CONFIRM2
            if [ "$CONFIRM2" = "destroy" ]; then
                print_info "Running terraform destroy..."
                terraform destroy
            else
                print_error "Destroy cancelled - confirmation text did not match"
                exit 0
            fi
        else
            print_error "Destroy cancelled by user"
            exit 0
        fi
        ;;
    "output")
        print_info "Showing terraform outputs..."
        terraform output
        ;;
    "init")
        print_info "Initializing terraform..."
        terraform init
        ;;
    "refresh")
        print_info "Refreshing terraform state..."
        terraform refresh
        ;;
    "shell")
        print_info "Opening shell with environment loaded..."
        print_success "Environment variables are loaded. You can now run terraform commands directly."
        print_info "Type 'exit' to return to normal shell."
        bash
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        show_usage
        exit 1
        ;;
esac

print_success "Command completed successfully!"