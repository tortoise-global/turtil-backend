# GitHub Actions Workflows

This directory contains the CI/CD workflows for the Turtil Backend application, organized into separate files for better maintainability and clarity.

## Workflow Structure

### 🔄 Continuous Integration (`ci.yml`)
**Triggers:** Pull requests and pushes to `dev`/`main` branches  
**Purpose:** Code quality checks and validation

**Jobs:**
- **test**: Python linting, type checking, and unit tests
- **terraform-validate**: Terraform formatting and validation
- **docker-build**: Docker image build test

### 🚀 Development Deployment (`deploy-dev.yml`) 
**Triggers:** Pushes to `dev` branch  
**Environment:** `development`  
**Terraform Workspace:** `dev`

**Pipeline:**
1. Terraform infrastructure deployment with development settings
2. Import existing AWS resources (ECR, ALB)
3. Docker image build and push to ECR
4. Application deployment verification

### 🏭 Production Deployment (`deploy-prod.yml`)
**Triggers:** 
- Pushes to `main` branch
- Manual workflow dispatch (requires confirmation)

**Environment:** `production`  
**Terraform Workspace:** `prod`

**Pipeline:**
1. Production deployment confirmation (manual trigger)
2. Terraform infrastructure deployment with production settings
3. Import existing AWS resources (ECR, ALB, CloudFront)
4. Docker image build and push to ECR
5. Zero-downtime deployment with Auto Scaling Group refresh
6. Comprehensive deployment verification

## Environment Configuration

### Development Environment
- **Database:** RDS PostgreSQL t4g.micro
- **Scaling:** Single instance for cost efficiency
- **Debug:** Enabled
- **Domains:** `devapi.turtilcms.turtil.co`

### Production Environment  
- **Database:** Aurora Serverless v2 (auto-scaling)
- **Scaling:** Multi-AZ with auto-scaling
- **Debug:** Disabled
- **Domains:** `api.turtilcms.turtil.co`
- **CDN:** CloudFront distribution
- **Deployment:** Zero-downtime with health checks

## Secrets Required

All workflows require these GitHub repository secrets:

### AWS Configuration
```
AWS_ACCESS_KEY_ID          # IAM user access key
AWS_SECRET_ACCESS_KEY      # IAM user secret key  
AWS_REGION                 # Default: ap-south-1
ECR_ACCOUNT_ID            # AWS account ID for ECR
```

### Application Configuration
```
DATABASE_URL              # PostgreSQL connection string
SECRET_KEY                # JWT secret key
ALGORITHM                 # JWT algorithm (HS256)
ACCESS_TOKEN_EXPIRE_MINUTES # JWT expiration
PROJECT_NAME              # Project name (e.g., "turtil-backend")
VERSION                   # Application version
LOG_LEVEL                 # Logging level
RATE_LIMIT_CALLS          # API rate limiting
RATE_LIMIT_PERIOD         # Rate limit period
OTP_EXPIRY_MINUTES        # OTP expiration time
OTP_MAX_ATTEMPTS          # Maximum OTP attempts
```

### Redis Configuration
```
UPSTASH_REDIS_URL         # Upstash Redis endpoint
UPSTASH_REDIS_TOKEN       # Upstash Redis auth token
REDIS_USER_CACHE_TTL      # User cache TTL
REDIS_BLACKLIST_TTL       # Token blacklist TTL
```

### AWS Services
```
AWS_SES_FROM_EMAIL        # SES from email address
AWS_SES_REGION            # SES region
```

**Note:** S3 bucket names and ECR repository names are automatically derived from `PROJECT_NAME` + environment:
- S3 Storage: `{PROJECT_NAME}-{environment}-storage`
- S3 Logs: `{PROJECT_NAME}-{environment}-logs`  
- ECR Repository: `{PROJECT_NAME}-{environment}`

## Key Features

### 🔄 Zero-Downtime Deployment
- Auto Scaling Group instance refresh with `MinHealthyPercentage: 100`
- Progressive rollout with checkpoint validation
- Automatic rollback on deployment failure
- Health check verification at each stage

### 🏗️ Infrastructure Import
- Automatic import of existing AWS resources
- Prevents resource recreation and downtime
- Handles ECR repositories, ALBs, and CloudFront distributions

### 🐳 Multi-Tag Docker Strategy
- `latest`: Current deployment
- `{environment}`: Environment-specific tag
- `{commit-sha}`: Exact commit tracking

### 🛡️ Production Safety
- Manual confirmation required for production deployments
- Extended health checks and monitoring
- Comprehensive error reporting and debugging

## Migration from Legacy

The original monolithic workflow (`deploy-legacy.yml`) has been split into:
- **CI validation** → `ci.yml`
- **Development deployment** → `deploy-dev.yml`  
- **Production deployment** → `deploy-prod.yml`

### Benefits of New Structure
1. **Clarity**: Each workflow has a single, clear purpose
2. **Maintainability**: Easier to modify environment-specific logic
3. **Performance**: Parallel execution of independent checks
4. **Safety**: Production-specific safeguards and validation
5. **Debugging**: Easier troubleshooting with focused workflows

## Usage Examples

### Development Deployment
```bash
# Automatic trigger
git push origin dev

# The dev deployment will:
# 1. Run Terraform with development.tfvars
# 2. Deploy to development environment
# 3. Verify deployment health
```

### Production Deployment
```bash
# Automatic trigger (main branch)
git push origin main

# Manual trigger with confirmation
# Go to GitHub Actions → Deploy to Production → Run workflow
# Enter: DEPLOY_TO_PRODUCTION

# The production deployment will:
# 1. Require confirmation
# 2. Run Terraform with production.tfvars  
# 3. Execute zero-downtime deployment
# 4. Comprehensive verification
```

### CI Validation Only
```bash
# Triggered on pull requests
git push origin feature-branch
# Creates PR → Triggers CI workflow

# Runs:
# - Code quality checks
# - Terraform validation
# - Docker build test
```

---

**Note:** The legacy workflow file (`deploy-legacy.yml`) is preserved for reference but is no longer active.