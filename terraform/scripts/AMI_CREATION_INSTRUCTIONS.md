# Custom Docker-Ready AMI Creation Instructions

This guide walks you through creating a custom AMI with Docker pre-installed for faster deployments.

## Prerequisites

1. AWS CLI configured with appropriate permissions
2. A valid EC2 key pair
3. Access to launch EC2 instances in your AWS account

## Step 1: Update Configuration

Before creating the AMI, update the configuration in `create-ami-locally.sh`:

```bash
# Edit terraform/scripts/create-ami-locally.sh
KEY_NAME="your-key-pair-name"        # Replace with your key pair
SECURITY_GROUP="sg-0123456789abcdef0" # Replace with your security group
SUBNET_ID="subnet-0123456789abcdef0"  # Replace with your subnet
```

## Step 2: Create the AMI

Run the AMI creation script:

```bash
cd terraform/scripts
chmod +x create-ami-locally.sh
chmod +x create-docker-ami.sh
./create-ami-locally.sh
```

The script will:
1. Launch an Ubuntu 24.04 LTS ARM64 instance
2. Provide SSH instructions
3. Wait for you to run the preparation script
4. Create the AMI
5. Clean up the temporary instance

## Step 3: Run Preparation Script on Instance

When prompted, SSH into the instance and run:

```bash
# SSH into the instance (provided by the script)
ssh -i ~/.ssh/your-key.pem ubuntu@PUBLIC_IP

# Download and run the preparation script
wget https://raw.githubusercontent.com/tortoise-global/turtil-backend/dev/terraform/scripts/create-docker-ami.sh
chmod +x create-docker-ami.sh
./create-docker-ami.sh

# Wait for completion, then logout
logout
```

## Step 4: Update Environment Files

After AMI creation, update all environment files with the new AMI ID:

```bash
# The script will output something like:
# AMI ID: ami-0a1b2c3d4e5f6g7h8

# Update environment files
# Replace 'ami-placeholder-will-be-updated-after-creation' with the actual AMI ID
```

Update these files:
- `.env.dev`
- `.env.test`
- `.env.prod`
- `.env.local`

## Step 5: Update GitHub Secrets

Add the new AMI ID to GitHub secrets for all environments:

```bash
gh secret set CUSTOM_AMI_ID --body "ami-0a1b2c3d4e5f6g7h8" --env dev
gh secret set CUSTOM_AMI_ID --body "ami-0a1b2c3d4e5f6g7h8" --env test
gh secret set CUSTOM_AMI_ID --body "ami-0a1b2c3d4e5f6g7h8" --env prod
```

## Step 6: Test Deployment

Deploy using the new AMI:

```bash
cd terraform
source ./scripts/loadenv.sh dev
terraform plan -var-file="environments/dev.tfvars"
terraform apply -var-file="environments/dev.tfvars"
```

## Benefits

After completing this setup:

- ✅ **Faster Deployments**: No Docker installation time (saves 2-3 minutes)
- ✅ **Consistent Environment**: All tools pre-installed and configured
- ✅ **Reliable Deployments**: No network dependency for package installation
- ✅ **Environment Parity**: Same AMI across dev, test, and prod

## AMI Contents

The custom AMI includes:
- Ubuntu 24.04 LTS ARM64
- Docker Engine (latest stable)
- Docker Compose (latest stable)
- Nginx (latest stable)
- AWS CLI v2 (latest)
- Essential utilities (curl, unzip, vim, git, htop)

## Troubleshooting

### AMI Creation Fails
- Verify your AWS permissions include EC2 and IAM access
- Check security group allows SSH (port 22) access
- Ensure key pair exists in the correct region

### Instance Launch Fails
- Verify the security group and subnet exist
- Check if you have available EC2 limits in your account
- Ensure the key pair name is correct

### Deployment Still Slow
- Verify the AMI ID is correctly set in environment variables
- Check terraform is using `var.custom_ami_id` not a hardcoded AMI
- Confirm the AMI is in the same region as your deployment