# Turtil Backend

Production-ready FastAPI backend for college management system with comprehensive CMS APIs, local authentication, and AWS S3 integration.

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

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload
```

## API Endpoints

### Authentication (`/cms/auth`)
- `POST /cms/auth/signup` - User registration
- `POST /cms/auth/login` - User authentication 
- `POST /cms/auth/send-email` - Send OTP to email
- `POST /cms/auth/verify-email` - Verify email with OTP
- `POST /cms/auth/change-password` - Change user password
- `GET /cms/auth/users/{user_id}` - Get user details
- `PUT /cms/auth/users/{user_id}` - Update user
- `DELETE /cms/auth/users/{user_id}` - Delete user
- `GET /cms/auth/fetch-users` - List users with pagination

### College Degrees (`/cms/college-degree`)
- `POST /cms/college-degree/collegedegree/` - Add college degree
- `PUT /cms/college-degree/collegedegree/{college_id}` - Update degree
- `DELETE /cms/college-degree/collegedegree/{college_id}` - Delete degree
- `GET /cms/college-degree/collegedegree/id/{college_id}` - Get by ID
- `GET /cms/college-degree/collegedegree/shortname/{short_name}` - Get by name

### College Placements (`/cms/college-placements`)
- `POST /cms/college-placements/collegeplacements/` - Add placement
- `GET /cms/college-placements/collegeplacements/{id}` - Get placement
- `PUT /cms/college-placements/collegeplacements/{id}` - Update placement
- `DELETE /cms/college-placements/collegeplacements/{id}` - Delete placement

### College Students (`/cms/college-students`)
- `POST /cms/college-students/college-students` - Create student
- `GET /cms/college-students/college-students` - List students (with filters)
- `GET /cms/college-students/college-students/{student_id}` - Get student
- `PUT /cms/college-students/college-students/{student_id}` - Update student
- `DELETE /cms/college-students/college-students/{student_id}` - Delete student
- `GET /cms/college-students/search-students` - Search students

### File Upload (`/cms/image-upload`)
- `POST /cms/image-upload/get-presigned-url` - Generate S3 presigned URL
- `DELETE /cms/image-upload/delete-file` - Delete file from S3
- `GET /cms/image-upload/bucket-status` - Check S3 bucket status

## Environment Variables

Copy `.env.example` to `.env` and update with your values:

```env
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/turtil_db

# Security
SECRET_KEY=your-super-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# OTP Configuration
OTP_SECRET=123456
OTP_EXPIRY_MINUTES=5

# AWS Configuration (from Terraform outputs)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-s3-bucket-name

# Application Settings
PROJECT_NAME=Turtil Backend
VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true

# CORS Settings
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]
ALLOWED_HOSTS=["localhost", "127.0.0.1", "0.0.0.0"]
```

## Authentication

The system uses **local PostgreSQL authentication** with JWT tokens:

1. **Sign up** a new user via `/cms/auth/signup`
2. **Login** with email/username and password via `/cms/auth/login` 
3. **Use the JWT token** in the `Authorization: Bearer <token>` header
4. **OTP verification** uses the value from `OTP_SECRET` environment variable

### Example Authentication Flow

```bash
# 1. Sign up
curl -X POST "http://localhost:8000/cms/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "yourpassword"}'

# 2. Login
curl -X POST "http://localhost:8000/cms/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"userName": "user@example.com", "Password": "yourpassword"}'

# 3. Use token in subsequent requests
curl -X GET "http://localhost:8000/cms/auth/users/user_id" \
  -H "Authorization: Bearer <your-jwt-token>"
```

## File Upload with S3

The `/cms/image-upload/get-presigned-url` endpoint generates secure presigned URLs for direct browser uploads to S3:

```bash
# 1. Get presigned URL
curl -X POST "http://localhost:8000/cms/image-upload/get-presigned-url" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"file_name": "image.jpg"}'

# 2. Upload file directly to S3 using the presigned URL
curl -X PUT "<presigned-url>" \
  -H "Content-Type: image/jpeg" \
  --data-binary @image.jpg
```

## Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Infrastructure Management

### Terraform Commands

```bash
cd terraform

# Initialize Terraform
terraform init

# Plan changes
terraform plan

# Apply changes
terraform apply

# Get outputs
terraform output

# Destroy infrastructure (⚠️ Warning: Deletes all resources)
terraform destroy
```

### Adding CloudFront (Future)

The Terraform configuration is designed to be extended. To add CloudFront CDN:

1. Add CloudFront configuration to `terraform/main.tf`
2. Update outputs to include CloudFront domain
3. Update application to use CloudFront URLs

## API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Development

### Project Structure

```
turtil-backend/
├── app/
│   ├── api/cms/          # CMS API routes
│   ├── core/             # Core utilities (auth, config, security)
│   ├── db/               # Database configuration
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic (S3, etc.)
│   └── main.py           # FastAPI application
├── terraform/            # Infrastructure as Code
├── alembic/              # Database migrations
├── requirements.txt      # Python dependencies
└── docker-compose.yml    # Docker services
```

### Adding New Features

1. **Add database model** in `app/models/models.py`
2. **Create Pydantic schemas** in `app/schemas/`
3. **Implement API routes** in `app/api/cms/`
4. **Add business logic** in `app/services/`
5. **Create migration** with `alembic revision --autogenerate`

## Security Features

- ✅ **BCrypt password hashing**
- ✅ **JWT token authentication**
- ✅ **CORS protection** 
- ✅ **Rate limiting**
- ✅ **SQL injection protection** (SQLAlchemy ORM)
- ✅ **S3 bucket security** (private, encrypted)
- ✅ **Environment variable security**

## Troubleshooting

### Common Issues

1. **Database connection errors**: Check PostgreSQL is running and `DATABASE_URL` is correct
2. **S3 permissions errors**: Verify AWS credentials and bucket exists
3. **Authentication failures**: Ensure JWT token is valid and not expired
4. **CORS errors**: Check `CORS_ORIGINS` includes your frontend URL

### Logs

```bash
# View application logs
docker-compose logs -f turtil-backend

# View database logs  
docker-compose logs -f postgres
```
