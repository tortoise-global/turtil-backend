#!/bin/bash

# Local Terraform Init Script
# Usage: ./local-init.sh

set -e

echo "🚀 Initializing Terraform for Local Development"
echo "================================================"

# Load environment variables from .env
echo "📋 Loading environment variables from .env..."
source ./loadenv.sh

# Initialize Terraform
echo "🔧 Running terraform init..."
terraform init

# Create or select local workspace
echo "🏗️  Setting up local workspace..."
WORKSPACE="local"
if terraform workspace list | grep -q "$WORKSPACE"; then
    echo "✅ Switching to existing workspace: $WORKSPACE"
    terraform workspace select $WORKSPACE
else
    echo "✨ Creating new workspace: $WORKSPACE"
    terraform workspace new $WORKSPACE
fi

echo ""
echo "✅ Local Terraform initialization completed!"
echo ""
echo "Next steps:"
echo "  ./local-plan.sh    # Plan your changes"
echo "  ./local-apply.sh   # Apply your changes"
echo "  ./local-destroy.sh # Destroy resources (careful!)"