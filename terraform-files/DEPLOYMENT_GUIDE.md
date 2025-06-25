# 🚀 Deployment Guide - Dev Environment

## Prerequisites

### 1. GitHub Environment Setup
Create a `dev` environment in your GitHub repository:
```
Repository → Settings → Environments → New Environment → "dev"
```

### 2. Required GitHub Secrets (Dev Environment)
Add these secrets to the `dev` environment:

#### Bootstrap Secrets (Required for first deployment)
```bash
AWS_ACCESS_KEY_ID=your-dev-aws-access-key
AWS_SECRET_ACCESS_KEY=your-dev-aws-secret-key
SECRET_KEY=your-64-char-secret-key-for-dev
UPSTASH_REDIS_URL=https://your-dev-redis.upstash.io
UPSTASH_REDIS_TOKEN=your-dev-redis-token
AWS_SES_FROM_EMAIL=support@turtil.co
```

**Note**: OTP_SECRET is not required as the application uses a fixed dev OTP (123456) for development.

#### Auto-Generated Secrets (Created by Terraform)
These will be automatically populated after first deployment:
```bash
DATABASE_URL=postgresql+asyncpg://...
S3_BUCKET_NAME=turtil-backend-dev-s3
ALB_DNS_NAME=turtil-backend-dev-alb-xxx.elb.amazonaws.com
ECR_REPOSITORY_URL=033464272864.dkr.ecr.ap-south-2.amazonaws.com/turtil-backend
CUSTOM_AMI_ID=ami-xxxxxxxxx
```

## Deployment Process

### Step 1: Initial Infrastructure Deployment
```bash
# Push to dev branch to trigger deployment
git checkout dev
git push origin dev
```

This will:
1. ✅ Create/find custom AMI with Docker pre-installed
2. ✅ Deploy VPC with public/private subnets
3. ✅ Create RDS PostgreSQL instance (db.t4g.small with destroy protection)
4. ✅ Set up S3 bucket for file uploads
5. ✅ Create ECR repository for Docker images
6. ✅ Deploy ALB + Auto Scaling Group
7. ✅ Auto-populate GitHub secrets with resource URLs

### Step 2: Application Deployment
The GitHub Actions workflow automatically:
1. ✅ Builds Docker image from `turtil-backend/` directory
2. ✅ Pushes image to ECR with tags: `dev` and `latest`
3. ✅ Triggers ASG instance refresh for zero-downtime deployment
4. ✅ Verifies deployment with health checks

## Infrastructure Created

### Core Resources (All prefixed with `turtil-backend-dev-`)
```
VPC & Networking:
├── VPC: turtil-backend-dev-vpc (10.0.0.0/16)
├── Public Subnets: 10.0.1.0/24, 10.0.2.0/24
├── Private Subnets: 10.0.10.0/24, 10.0.11.0/24
├── Internet Gateway + NAT Gateways
└── Security Groups (ALB, EC2, RDS)

Database:
├── RDS: turtil-backend-dev-rds
├── Instance: db.t4g.small (ARM64)
├── Database: turtil-backend-dev
├── Destroy Protection: ✅ ENABLED
└── Public Access: ✅ Enabled (dev only)

Compute:
├── ALB: turtil-backend-dev-alb
├── Target Group: turtil-backend-dev-tg
├── ASG: turtil-backend-dev-asg
├── Launch Template: t4g.medium instances
└── Custom AMI: Pre-installed Docker/Nginx/AWS CLI

Storage:
├── S3: turtil-backend-dev-s3
├── ECR: turtil-backend (shared across environments)
└── Versioning & Encryption: ✅ Enabled
```

## Local Development Access

### Get Dev Resources
```bash
# Database connection
gh secret get DATABASE_URL --env dev

# S3 bucket name
gh secret get S3_BUCKET_NAME --env dev

# Application endpoint
gh secret get ALB_DNS_NAME --env dev
```

### Quick Setup
```bash
# Create local environment
echo "DATABASE_URL=$(gh secret get DATABASE_URL --env dev)" > .env.local
source .env.local

# Test application
ALB_DNS=$(gh secret get ALB_DNS_NAME --env dev)
curl "http://$ALB_DNS/health"
```

## Deployment Verification

### Health Checks
```bash
ALB_DNS=$(gh secret get ALB_DNS_NAME --env dev)

# Basic health check
curl "http://$ALB_DNS/health"

# Detailed health check
curl "http://$ALB_DNS/health/detailed"
```

### Resource Verification
```bash
# Check RDS instance
aws rds describe-db-instances --db-instance-identifier turtil-backend-dev-rds

# Check S3 bucket
aws s3 ls s3://turtil-backend-dev-s3/

# Check ECR repository
aws ecr describe-repositories --repository-names turtil-backend

# Check ASG health
aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names turtil-backend-dev-asg
```

## Troubleshooting

### Common Issues

#### 1. First Deployment Fails
**Problem**: Missing GitHub secrets
**Solution**: Ensure all bootstrap secrets are added to dev environment

#### 2. AMI Creation Takes Long
**Problem**: Custom AMI creation is slow
**Solution**: Wait ~10-15 minutes for AMI creation on first deployment

#### 3. Health Checks Fail
**Problem**: Application not responding
**Solution**: Check Docker container logs:
```bash
# SSH to instance (if needed)
aws ssm start-session --target i-xxxxxxxxx

# Check container status
docker ps
docker logs turtil-backend
```

#### 4. Database Connection Issues
**Problem**: Cannot connect to RDS
**Solution**: Check security groups and connection string:
```bash
# Test database connectivity
DATABASE_URL=$(gh secret get DATABASE_URL --env dev)
psql "$DATABASE_URL" -c "SELECT 1;"
```

### Logs and Monitoring
```bash
# Application logs via CloudWatch
aws logs describe-log-groups --log-group-name-prefix turtil-backend

# Instance logs via Systems Manager
aws ssm start-session --target i-xxxxxxxxx
tail -f /var/log/user-data.log
```

## Next Steps

After successful dev deployment:

1. **Test thoroughly** in dev environment
2. **Copy setup** for test environment (when ready)
3. **Copy setup** for production environment (when ready)
4. **Set up monitoring** and alerting
5. **Configure CI/CD** for automatic deployments

---

## Security Notes

- ✅ **RDS**: Destroy protection enabled
- ✅ **S3**: Encryption and versioning enabled  
- ✅ **EBS**: Encrypted volumes
- ✅ **ALB**: SSL ready (certificate needed for HTTPS)
- ✅ **Secrets**: Managed via GitHub environment secrets
- ✅ **IAM**: Least privilege access policies

---

**📞 Support**: For issues, check GitHub Actions logs and AWS CloudWatch for detailed error information.