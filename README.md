# Turtil Backend

Production-ready FastAPI backend for college management system with student and CSM (College/System Management) APIs.

## Features

- FastAPI with SQLAlchemy and Alembic migrations
- PostgreSQL database
- Docker containerization
- Student management API (`/student`)
- CSM (College System Management) API (`/csm`)
- Virtual environment setup

## Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Clone and navigate to project
cd turtil-backend

# Start all services (API + PostgreSQL)
docker-compose up -d

# API will be available at http://localhost:8000
```

### Option 2: Local Development

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

## Environment Variables

Copy `.env.example` to `.env` and update:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/turtil_db
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
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

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
