# 🔗 Local Access to Dev Resources

## Get Dev Environment Resources

After infrastructure deployment, use GitHub CLI to access dev resources locally:

### Prerequisites
```bash
# Install GitHub CLI
# macOS: brew install gh
# Ubuntu: sudo apt install gh

# Authenticate
gh auth login

# Set default repository
gh repo set-default your-org/turtil-backend
```

### Get Resource URLs
```bash
# Database connection for local development
gh secret get DATABASE_URL --env dev

# S3 bucket for file uploads
gh secret get S3_BUCKET_NAME --env dev

# Application load balancer endpoint
gh secret get ALB_DNS_NAME --env dev

# ECR repository for Docker images
gh secret get ECR_REPOSITORY_URL --env dev

# Custom AMI ID
gh secret get CUSTOM_AMI_ID --env dev
```

### Quick Local Setup
```bash
# Create local environment file
echo "DATABASE_URL=$(gh secret get DATABASE_URL --env dev)" > .env.local
echo "S3_BUCKET_NAME=$(gh secret get S3_BUCKET_NAME --env dev)" >> .env.local
echo "AWS_REGION=ap-south-2" >> .env.local
echo "AWS_SES_REGION=ap-south-1" >> .env.local

# Load environment
source .env.local

# Connect to dev database
psql "$DATABASE_URL"
```

### Test Dev Environment
```bash
# Get ALB DNS name
ALB_DNS=$(gh secret get ALB_DNS_NAME --env dev)

# Test health endpoint
curl "http://$ALB_DNS/health"

# Test detailed health
curl "http://$ALB_DNS/health/detailed"
```

## Dev Environment Resources

All dev resources use the prefix `turtil-backend-dev-`:

- **VPC**: `turtil-backend-dev-vpc`
- **Database**: `turtil-backend-dev-rds` (PostgreSQL db.t4g.small)
- **S3 Bucket**: `turtil-backend-dev-s3`
- **Load Balancer**: `turtil-backend-dev-alb`
- **Auto Scaling Group**: `turtil-backend-dev-asg`

## Direct AWS CLI Access

If needed, you can also access resources directly:

```bash
# List RDS instances
aws rds describe-db-instances --query 'DBInstances[?DBInstanceIdentifier==`turtil-backend-dev-rds`]'

# Get ALB information
aws elbv2 describe-load-balancers --names turtil-backend-dev-alb

# List S3 buckets
aws s3 ls | grep turtil-backend-dev

# Get ECR repository info
aws ecr describe-repositories --repository-names turtil-backend
```

## Development Database Access

The dev database is configured for external access (dev environment only):

```bash
# Connection details
DATABASE_URL=$(gh secret get DATABASE_URL --env dev)

# Extract components
DB_HOST=$(echo "$DATABASE_URL" | cut -d'@' -f2 | cut -d':' -f1)
DB_PORT=5432
DB_NAME=turtil_backend_dev

# Connect with psql
psql "$DATABASE_URL"

# Or with connection details
psql -h "$DB_HOST" -p 5432 -U turtil_admin -d turtil_backend_dev
```

---

**Security Note**: Dev environment allows external database access for development convenience. Test and prod environments will have private database access only.