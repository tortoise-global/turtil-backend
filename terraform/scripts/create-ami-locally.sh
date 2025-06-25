#!/bin/bash

# ============================================================================
# LOCAL AMI CREATION SCRIPT
# ============================================================================
# This script creates a custom Docker-ready AMI locally using AWS CLI

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

# Configuration
BASE_AMI="ami-0eb4445f6c0a650a1"  # Ubuntu Server Pro 24.04 LTS ARM64
INSTANCE_TYPE="t4g.micro"
KEY_NAME="your-key-pair-name"  # Update this with your key pair name
SECURITY_GROUP="sg-0123456789abcdef0"  # Update this with your security group
SUBNET_ID="subnet-0123456789abcdef0"  # Update this with your subnet

AMI_NAME="turtil-backend-docker-ubuntu-24.04-arm64"
AMI_DESCRIPTION="Ubuntu 24.04 LTS ARM64 with Docker, docker-compose, nginx, and AWS CLI pre-installed for Turtil Backend"

echo "🚀 Creating Custom Docker-Ready AMI"
echo "===================================="
print_info "Base AMI: $BASE_AMI (Ubuntu Server Pro 24.04 LTS ARM64)"
print_info "Instance Type: $INSTANCE_TYPE"
print_info "Target AMI Name: $AMI_NAME"
echo ""

print_warning "Please ensure you have:"
echo "1. AWS CLI configured with appropriate permissions"
echo "2. Valid key pair name updated in this script"
echo "3. Valid security group ID updated in this script"
echo "4. Valid subnet ID updated in this script"
echo ""

read -p "🤔 Continue with AMI creation? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    print_error "AMI creation cancelled by user"
    exit 0
fi

# Step 1: Launch EC2 instance
print_info "Step 1: Launching EC2 instance..."
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id $BASE_AMI \
    --instance-type $INSTANCE_TYPE \
    --key-name $KEY_NAME \
    --security-group-ids $SECURITY_GROUP \
    --subnet-id $SUBNET_ID \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=turtil-ami-builder},{Key=Purpose,Value=ami-creation}]" \
    --query 'Instances[0].InstanceId' \
    --output text)

print_success "Instance launched: $INSTANCE_ID"

# Step 2: Wait for instance to be running
print_info "Step 2: Waiting for instance to be running..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID
print_success "Instance is running"

# Step 3: Get instance public IP
PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)
print_info "Instance Public IP: $PUBLIC_IP"

# Step 4: Wait a bit more for SSH to be ready
print_info "Step 3: Waiting for SSH to be ready..."
sleep 60

print_warning "Manual Steps Required:"
echo ""
echo "1. SSH into the instance:"
echo "   ssh -i ~/.ssh/$KEY_NAME.pem ubuntu@$PUBLIC_IP"
echo ""
echo "2. Run the preparation script:"
echo "   wget https://raw.githubusercontent.com/your-repo/turtil-backend/dev/terraform/scripts/create-docker-ami.sh"
echo "   chmod +x create-docker-ami.sh"
echo "   ./create-docker-ami.sh"
echo ""
echo "3. Or copy and run the script manually from your local machine"
echo ""
print_warning "Press ENTER when the preparation script has completed and you're ready to create the AMI..."
read

# Step 5: Stop the instance
print_info "Step 4: Stopping instance for AMI creation..."
aws ec2 stop-instances --instance-ids $INSTANCE_ID
aws ec2 wait instance-stopped --instance-ids $INSTANCE_ID
print_success "Instance stopped"

# Step 6: Create AMI
print_info "Step 5: Creating AMI..."
AMI_ID=$(aws ec2 create-image \
    --instance-id $INSTANCE_ID \
    --name "$AMI_NAME" \
    --description "$AMI_DESCRIPTION" \
    --no-reboot \
    --tag-specifications "ResourceType=image,Tags=[{Key=Name,Value=$AMI_NAME},{Key=Project,Value=turtil-backend},{Key=OS,Value=ubuntu-24.04},{Key=Architecture,Value=arm64}]" \
    --query 'ImageId' \
    --output text)

print_success "AMI creation initiated: $AMI_ID"

# Step 7: Wait for AMI to be available
print_info "Step 6: Waiting for AMI to be available (this may take several minutes)..."
aws ec2 wait image-available --image-ids $AMI_ID
print_success "AMI is available!"

# Step 8: Terminate the instance
print_info "Step 7: Terminating temporary instance..."
aws ec2 terminate-instances --instance-ids $INSTANCE_ID
print_success "Temporary instance terminated"

# Step 9: Display results
echo ""
print_success "🎉 Custom AMI Created Successfully!"
echo "=================================="
print_info "AMI ID: $AMI_ID"
print_info "AMI Name: $AMI_NAME"
print_info "Architecture: ARM64"
print_info "Region: $(aws configure get region)"
echo ""

print_warning "Next Steps:"
echo "1. Update environment files with: CUSTOM_AMI_ID=$AMI_ID"
echo "2. Update terraform configuration to use the custom AMI"
echo "3. Update GitHub secrets with the new AMI ID"
echo "4. Test deployment with the new AMI"
echo ""

# Step 10: Save AMI ID to file
echo "CUSTOM_AMI_ID=$AMI_ID" > custom-ami-id.txt
print_info "AMI ID saved to: custom-ami-id.txt"

print_success "AMI creation process completed!"