# Turtil Backend

backend for college management system with comprehensive CMS APIs, local authentication, and AWS S3 integration.

## Features

- **FastAPI** with SQLAlchemy and Alembic migrations
- **PostgreSQL** database with local authentication (JWT)
- **AWS S3** integration for file uploads with presigned URLs
- **Docker** containerization
- **Terraform** infrastructure as code for AWS resources
- **CMS APIs** for college management:
  - Authentication & User Management
  - Student Management
  - College Degree Management
  - Placement Tracking
  - File Upload System
- **Security**: BCrypt password hashing, JWT tokens, CORS protection
- **OTP Verification** system

## Quick Start

### Prerequisites

1. **Python 3.8+** and pip
2. **PostgreSQL** (via Docker or local installation)
3. **AWS Account** (for S3 file uploads)
4. **Terraform** (for AWS infrastructure setup)

### Step 1: Setup AWS Infrastructure

```bash
# Navigate to terraform directory
cd terraform

# Copy example variables and customize
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your unique S3 bucket name

# Initialize and apply Terraform
terraform init
terraform plan
terraform apply

# Get AWS credentials for your .env file
terraform output -json env_variables
```

### Step 2: Environment Setup

```bash
# Copy environment file
cp .env.example .env

# Update .env with Terraform outputs:
# AWS_ACCESS_KEY_ID=<from terraform output>
# AWS_SECRET_ACCESS_KEY=<from terraform output>
# AWS_REGION=<from terraform output>
# S3_BUCKET_NAME=<from terraform output>
```

### Step 3: Application Setup

#### Option A: Docker Compose (Recommended)

```bash
# Start all services (API + PostgreSQL)
docker-compose up -d

# API will be available at http://localhost:8000
```

#### Option B: Local Development

```bash
# Start PostgreSQL only
cd db && docker-compose up -d

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install --upgrade pip


# Install dependencies
pip install -r requirements.txt

or

rm -rf venv && python3.12 -m venv venv && source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload
```
