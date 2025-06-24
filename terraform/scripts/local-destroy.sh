#!/bin/bash

# Local Terraform Destroy Script
# Usage: ./local-destroy.sh [environment]

set -e

# Default to dev environment
ENVIRONMENT=${1:-dev}

echo "💥 Destroying Terraform Resources for Local Development"
echo "======================================================="
echo "Environment: $ENVIRONMENT"
echo ""

# Load environment variables from .env
echo "📋 Loading environment variables from .env..."
source ./loadenv.sh

# Check if we're in the correct workspace
CURRENT_WORKSPACE=$(terraform workspace show)
if [ "$CURRENT_WORKSPACE" != "local" ]; then
    echo "⚠️  Current workspace: $CURRENT_WORKSPACE"
    echo "🔄 Switching to local workspace..."
    terraform workspace select local || terraform workspace new local
fi

# Determine which tfvars file to use
TFVARS_FILE="environments/${ENVIRONMENT}.tfvars"

if [ ! -f "$TFVARS_FILE" ]; then
    echo "❌ Error: $TFVARS_FILE not found!"
    echo "Available environments:"
    ls -1 environments/*.tfvars | sed 's/environments\///g' | sed 's/\.tfvars//g'
    exit 1
fi

echo "📁 Using variables file: $TFVARS_FILE"
echo ""

# Strong confirmation prompt
echo "⚠️  WARNING: This will PERMANENTLY DESTROY all resources!"
echo "⚠️  Environment: $ENVIRONMENT"
echo "⚠️  Workspace: $CURRENT_WORKSPACE"
echo ""
read -p "🔥 Type 'DESTROY' to confirm you want to destroy all resources: " CONFIRM
if [ "$CONFIRM" != "DESTROY" ]; then
    echo "❌ Destroy cancelled by user"
    exit 0
fi

echo ""
read -p "🤔 Are you absolutely sure? This cannot be undone! (yes/no): " FINAL_CONFIRM
if [ "$FINAL_CONFIRM" != "yes" ]; then
    echo "❌ Destroy cancelled by user"
    exit 0
fi

# Run terraform destroy
echo "💥 Running terraform destroy..."
terraform destroy -var-file="$TFVARS_FILE" -auto-approve

echo ""
echo "✅ Terraform destroy completed!"
echo ""
echo "🗑️  All resources have been destroyed for environment: $ENVIRONMENT"