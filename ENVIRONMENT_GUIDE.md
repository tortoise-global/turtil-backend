# 🌍 Environment Switching Guide

After one-time setup, you can easily switch between environments for testing.

## 🚀 Quick Environment Switching

### **Local Development (Docker)**
```bash
export ENV_FILE=.env.local
python run.py
# Uses: Local PostgreSQL + Redis + MinIO S3
```

### **Development (AWS)**  
```bash
export ENV_FILE=.env.dev
python run.py
# Uses: AWS RDS + Upstash Redis + S3
```

### **Test (AWS)**
```bash
export ENV_FILE=.env.test  
python run.py
# Uses: AWS RDS + Upstash Redis + S3 + Load Balancer
```

### **Production (AWS)**
```bash
export ENV_FILE=.env.prod
python run.py  
# Uses: Aurora Serverless v2 + Upstash Redis + S3 + ALB + CloudFront
```

## 📋 Environment Status Check

### **Check Local Services**
```bash
# Check Docker services
cd db && docker-compose ps

# Test local connections
curl http://localhost:8079  # Redis HTTP
curl http://localhost:9000  # MinIO S3
psql postgresql://user:password@localhost:5432/turtil_db -c "SELECT 1;"
```

### **Check AWS Environments**
```bash
cd terraform

# Check dev environment
terraform workspace select dev
terraform output

# Check test environment  
terraform workspace select test
terraform output

# Check prod environment
terraform workspace select prod  
terraform output
```

## 🗄️ Database URLs (After Setup)

### **Local**
```
postgresql+asyncpg://user:password@localhost:5432/turtil_db
```

### **Development** 
```
postgresql+asyncpg://turtiluser:password@dev-rds-endpoint:5432/turtil-backend-dev
```

### **Test**
```
postgresql+asyncpg://turtiluser:password@test-rds-endpoint:5432/turtil-backend-test  
```

### **Production**
```
postgresql+asyncpg://turtiluser:password@prod-aurora-endpoint:5432/turtil-backend-prod
```

## 🪣 S3 Buckets (After Setup)

### **Local (MinIO)**
```
S3_BUCKET_NAME=turtil-backend-local
S3_ENDPOINT_URL=http://localhost:9000
```

### **AWS Environments**
```
# Development
S3_BUCKET_NAME=turtil-backend-dev-storage-randomsuffix

# Test  
S3_BUCKET_NAME=turtil-backend-test-storage-randomsuffix

# Production
S3_BUCKET_NAME=turtil-backend-prod-storage-randomsuffix
```

## 🚀 Upstash Redis URLs (After Setup)

### **Local (Docker)**
```
UPSTASH_REDIS_URL=http://localhost:8079
UPSTASH_REDIS_TOKEN=example_token
```

### **AWS Environments**
```
# Development
UPSTASH_REDIS_URL=https://your-dev-redis.upstash.io
UPSTASH_REDIS_TOKEN=your_dev_token

# Test
UPSTASH_REDIS_URL=https://your-test-redis.upstash.io  
UPSTASH_REDIS_TOKEN=your_test_token

# Production
UPSTASH_REDIS_URL=https://your-prod-redis.upstash.io
UPSTASH_REDIS_TOKEN=your_prod_token
```

## 🔍 Health Check URLs

### **Local**
```
http://localhost:8000/health
http://localhost:8000/health/detailed
```

### **Development (Single Instance)**
```
http://DEV_INSTANCE_IP:8000/health
```

### **Test/Production (Load Balancer)**
```
http://ALB_DNS_NAME/health
http://ALB_DNS_NAME/health/detailed
```

## 📱 Application Access

### **Local Development**
- **App**: `http://localhost:8000`
- **MinIO Console**: `http://localhost:9001` (admin/admin123)

### **Development**  
- **App**: `http://DEV_INSTANCE_IP:8000`
- **Direct access to single EC2 instance**

### **Test**
- **App**: `http://TEST_ALB_DNS`
- **Load balanced across multiple instances**

### **Production**
- **App**: `https://CLOUDFRONT_DOMAIN` 
- **CDN + Load balancer + Auto scaling**

## 🛠️ Development Workflow

### **1. Local Testing**
```bash
# Start local services
cd db && docker-compose up -d

# Run application locally
export ENV_FILE=.env.local
python run.py

# Test locally, no AWS costs
```

### **2. Development Testing** 
```bash
# Switch to dev environment
export ENV_FILE=.env.dev
python run.py

# Test with AWS RDS but cost-optimized
```

### **3. Integration Testing**
```bash
# Switch to test environment  
export ENV_FILE=.env.test
python run.py

# Test with full load balancer setup
```

### **4. Production Deployment**
```bash
# Use production environment
export ENV_FILE=.env.prod
python run.py

# Full production setup with Aurora + CloudFront
```

## 💰 Cost Summary

### **Local**: $0/month
- All services run in Docker locally

### **Development**: ~$15-20/month  
- RDS t4g.micro + S3 + Single EC2 (spot instance)
- No load balancer, cost optimized

### **Test**: ~$30-35/month
- RDS t4g.micro + S3 + ALB + ASG
- Production-like testing setup

### **Production**: ~$60-80/month
- Aurora Serverless v2 + S3 + ALB + ASG + CloudFront  
- Full high-availability setup

## 🎯 Quick Commands Reference

```bash
# Deploy all environments (one-time)
cd terraform && ./scripts/populate-env.sh all

# Start local development
cd db && docker-compose up -d && export ENV_FILE=.env.local

# Switch environments
export ENV_FILE=.env.dev    # Development
export ENV_FILE=.env.test   # Test  
export ENV_FILE=.env.prod   # Production
export ENV_FILE=.env.local  # Local Docker

# Check environment status
echo $ENV_FILE && python -c "import os; print(f'Environment: {os.getenv(\"ENVIRONMENT\", \"Not Set\")}')"
```