# Active Recall Monitor

A production-quality web application for tracking study subjects and generating daily review schedules using spaced repetition / active recall principles.

**Features secure multi-user authentication**, per-user data isolation, and production-ready security hardening.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Security Features](#security-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Production Readiness](#production-readiness)
- [Deployment](#deployment)
- [Code Walkthrough](#code-walkthrough)

## Overview

Active Recall Monitor helps you implement spaced repetition for your studies. Each user can:
- Add subjects (e.g., "Cardiology", "Pharmacology")
- Set a start date and review schedule
- See which subjects need review today
- Use default intervals `[1, 3, 7, 14, 30, 60, 120, 180]` days or create custom schedules

**Multi-user system**: Each user's data is completely isolated. Users can only see and manage their own subjects.

## Features

- **Secure Authentication**: Register/login with JWT tokens and Argon2 password hashing
- **Multi-User Support**: Complete data isolation between users
- **Dashboard**: Shows subjects due for review today (Europe/Bucharest timezone)
- **Subject Management**: Add, edit, and delete study subjects
- **Flexible Scheduling**: Use default intervals or create custom review schedules
- **Next Due Calculation**: See when each subject needs to be reviewed next
- **Beautiful UI**: Modern, responsive design with shadcn/ui components
- **API Documentation**: Interactive Swagger docs at `/docs`

## Security Features

| Feature | Implementation |
|---------|---------------|
| Password Hashing | Argon2 (memory-hard, GPU-resistant) |
| Authentication | JWT access tokens (15min) + refresh tokens (7 days) |
| Token Storage | Access tokens in memory, refresh in httpOnly cookies |
| CORS | Configurable allowed origins |
| Rate Limiting | Auth endpoints rate limited (5/min default) |
| User Isolation | All queries scoped by authenticated user |
| Security Headers | X-Content-Type-Options, X-Frame-Options, X-XSS-Protection |
| Input Validation | Pydantic validation on all inputs |
| Error Handling | Generic errors in production (no stack traces leaked) |

## Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│                 │      │                 │      │                 │
│  React Frontend │◄────►│  FastAPI Backend│◄────►│  SQLite DB      │
│  (Vite + TS)    │ HTTP │  (Python 3.11)  │      │  (SQLAlchemy)   │
│                 │      │                 │      │                 │
└─────────────────┘      └─────────────────┘      └─────────────────┘
     Port 5173                Port 7070              app.db file
```

## Tech Stack

### Backend
- **Python 3.11** - Modern Python with type hints
- **FastAPI** - High-performance async API framework
- **Uvicorn** - ASGI server
- **SQLAlchemy 2.0** - ORM with modern type annotations
- **Alembic** - Database migrations
- **Pydantic** - Data validation
- **Argon2** - Password hashing
- **python-jose** - JWT tokens
- **SlowAPI** - Rate limiting
- **Pytest** - Testing framework

### Frontend
- **React 18** - UI library
- **TypeScript** - Type-safe JavaScript
- **Vite** - Fast build tool
- **TailwindCSS** - Utility-first CSS
- **shadcn/ui** - Beautiful UI components
- **Lucide React** - Icon library
- **Axios** - HTTP client with interceptors
- **React Router** - Client-side routing

## Project Structure

```
active-recall/
├── backend/                    # Python FastAPI application
│   ├── app/
│   │   ├── api/               # API route handlers
│   │   │   ├── auth.py        # Auth endpoints (register/login/logout)
│   │   │   ├── health.py      # Health check
│   │   │   ├── subjects.py    # Subject CRUD (authenticated)
│   │   │   └── reviews.py     # Review queries (authenticated)
│   │   ├── core/              # Security and dependencies
│   │   │   ├── security.py    # Password hashing, JWT functions
│   │   │   └── deps.py        # FastAPI dependencies (get_current_user)
│   │   ├── models/            # SQLAlchemy ORM models
│   │   │   ├── user.py        # User model
│   │   │   └── subject.py     # Subject model (with user_id FK)
│   │   ├── schemas/           # Pydantic validation schemas
│   │   │   ├── auth.py        # Auth request/response schemas
│   │   │   ├── subject.py     # Subject schemas
│   │   │   └── review.py      # Review schemas
│   │   ├── services/          # Business logic layer
│   │   │   ├── auth_service.py    # Auth operations
│   │   │   ├── subject_service.py # Subject CRUD (user-scoped)
│   │   │   └── review_service.py  # Due date calculations
│   │   ├── config.py          # Configuration (env vars)
│   │   ├── database.py        # Database setup
│   │   └── main.py            # FastAPI application
│   ├── alembic/               # Database migrations
│   ├── tests/                 # Pytest test suite
│   │   ├── test_auth.py       # Auth endpoint tests
│   │   ├── test_user_isolation.py # Security isolation tests
│   │   └── ...
│   ├── requirements.txt       # Python dependencies
│   └── Dockerfile            # Backend container
│
├── frontend/                  # React application
│   ├── src/
│   │   ├── contexts/
│   │   │   └── AuthContext.tsx    # Auth state management
│   │   ├── components/
│   │   │   ├── ProtectedRoute.tsx # Route guard
│   │   │   └── ...
│   │   ├── pages/
│   │   │   ├── Login.tsx      # Login page
│   │   │   ├── Register.tsx   # Registration page
│   │   │   ├── Dashboard.tsx  # Today's reviews
│   │   │   └── Subjects.tsx   # Subject management
│   │   └── lib/
│   │       └── api.ts         # API client with auth
│   ├── package.json
│   └── Dockerfile
│
├── docker-compose.yml
├── run.sh                    # Development runner
└── README.md
```

## Getting Started

### Prerequisites

- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **npm** - Comes with Node.js

### Quick Start

```bash
# Clone and enter the repository
cd active-recall

# Make the run script executable
chmod +x run.sh

# Install all dependencies
./run.sh setup

# Start both backend and frontend
./run.sh
```

Then open:
- **Frontend**: http://localhost:5173
- **Backend API docs**: http://localhost:7070/docs

### Manual Setup

#### Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run the server on port 7070
uvicorn app.main:app --reload --host 0.0.0.0 --port 7070
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Running the Application

### Development Mode

**Option 1: Using run.sh (recommended)**
```bash
./run.sh           # Runs both backend (7070) and frontend (5173)
./run.sh backend   # Runs only backend on port 7070
./run.sh frontend  # Runs only frontend on port 5173
./run.sh setup     # Install all dependencies
```

**Option 2: Manual (two terminals)**

Terminal 1 - Backend:
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 7070
```

Terminal 2 - Frontend:
```bash
cd frontend
npm run dev
```

### Production Mode (Docker)

```bash
# Set required environment variable
export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(64))")

# Build and run
docker-compose up --build
```

## API Documentation

Interactive API documentation: http://localhost:7070/docs

### Auth Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/auth/register` | Register new user | No |
| POST | `/api/auth/login` | Login | No |
| POST | `/api/auth/logout` | Logout | No |
| GET | `/api/auth/me` | Get current user | Yes |
| POST | `/api/auth/refresh` | Refresh tokens | Cookie |

### Protected Endpoints (require authentication)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/subjects` | List user's subjects |
| POST | `/api/subjects` | Create a subject |
| GET | `/api/subjects/{id}` | Get a subject |
| PUT | `/api/subjects/{id}` | Update a subject |
| DELETE | `/api/subjects/{id}` | Delete a subject |
| GET | `/api/reviews/today?tz=...` | Today's reviews |
| GET | `/api/reviews/upcoming?days=7` | Upcoming reviews |

### Sample cURL Commands

```bash
# Register a new user
curl -X POST http://localhost:7070/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepassword123"}'

# Login (save the access_token)
curl -X POST http://localhost:7070/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepassword123"}'

# Create a subject (use token from login)
curl -X POST http://localhost:7070/api/subjects \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "name": "Cardiology",
    "start_date": "2026-01-25",
    "schedule_type": "DEFAULT"
  }'

# Get today's reviews
curl "http://localhost:7070/api/reviews/today?tz=Europe/Bucharest" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# List all subjects
curl http://localhost:7070/api/subjects \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Testing

### Run All Tests

```bash
cd backend
source venv/bin/activate

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_auth.py
pytest tests/test_user_isolation.py

# Run with coverage
pytest --cov=app
```

### Test Categories

- **test_auth.py**: Authentication (register, login, me, logout)
- **test_user_isolation.py**: Security - users can't access each other's data
- **test_api_subjects.py**: Subject CRUD operations
- **test_api_reviews.py**: Review query endpoints
- **test_review_service.py**: Due date calculation logic

## Production Readiness

### What's Safe Now

- **Password Security**: Argon2 with memory-hard parameters
- **Token Security**: Short-lived access tokens (15min), httpOnly refresh cookies
- **Input Validation**: All inputs validated with Pydantic
- **User Isolation**: Queries scoped by user, 404 for unauthorized access
- **Rate Limiting**: Auth endpoints protected against brute force
- **Security Headers**: Basic security headers included
- **Error Handling**: Generic errors in production mode

### What to Change for Production

| Setting | Development | Production |
|---------|-------------|------------|
| `JWT_SECRET_KEY` | Auto-generated (random) | Set via env var (required!) |
| `ENVIRONMENT` | `development` | `production` |
| `DEBUG` | `true` | `false` |
| `COOKIE_SECURE` | `false` | `true` (requires HTTPS) |
| `CORS_ORIGINS` | `localhost` | Your actual domain(s) |
| `DATABASE_URL` | SQLite file | PostgreSQL recommended |

### Production Deployment Checklist

1. **Generate a secure JWT secret**:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(64))"
   ```

2. **Set environment variables**:
   ```bash
   export JWT_SECRET_KEY="your-64-char-secret"
   export ENVIRONMENT="production"
   export DEBUG="false"
   export COOKIE_SECURE="true"
   export CORS_ORIGINS='["https://yourdomain.com"]'
   ```

3. **Use HTTPS**: Required for secure cookies

4. **Use a reverse proxy**: Nginx or Caddy recommended

5. **Switch to PostgreSQL** for production:
   ```bash
   export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
   ```

6. **Run migrations**:
   ```bash
   alembic upgrade head
   ```

## Deployment

### Docker on Raspberry Pi 5

```bash
# Generate JWT secret
export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(64))")

# Build and run
docker-compose up -d --build

# Access at http://<rpi-ip>:5173
```

### Switching to PostgreSQL

1. Install psycopg2:
   ```bash
   pip install psycopg2-binary
   ```

2. Update environment:
   ```bash
   export DATABASE_URL="postgresql://user:password@localhost:5432/active_recall"
   ```

3. Run migrations:
   ```bash
   alembic upgrade head
   ```

## Code Walkthrough

### For New Developers

#### Authentication Flow

1. **Registration** (`POST /api/auth/register`):
   - Validate email/password
   - Hash password with Argon2
   - Create user in database
   - Generate JWT access + refresh tokens
   - Return access token in body, refresh in httpOnly cookie

2. **Login** (`POST /api/auth/login`):
   - Validate credentials
   - Small delay on failure (brute force protection)
   - Update last_login_at
   - Return tokens same as registration

3. **Protected Request**:
   - Frontend sends `Authorization: Bearer <token>` header
   - `get_current_user` dependency validates token
   - Extracts user_id from JWT `sub` claim
   - Loads user from database
   - All queries scoped to that user

4. **Token Refresh** (`POST /api/auth/refresh`):
   - Uses refresh token from httpOnly cookie
   - Validates token type is "refresh"
   - Issues new access + refresh tokens

#### User Data Isolation

All services take `User` as constructor argument:

```python
class SubjectService:
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    def get_all(self) -> list[Subject]:
        # Automatically scoped to user
        return self.db.query(Subject).filter(
            Subject.user_id == self.user.id
        ).all()
```

Even if an attacker guesses a subject ID, they get 404 (not 403) to avoid confirming the resource exists.

#### Key Files to Understand

1. **`app/core/security.py`**: Password hashing, JWT creation/verification
2. **`app/core/deps.py`**: FastAPI dependencies for auth
3. **`app/services/auth_service.py`**: Registration, login logic
4. **`app/api/auth.py`**: Auth endpoints
5. **`frontend/src/contexts/AuthContext.tsx`**: React auth state
6. **`frontend/src/lib/api.ts`**: Axios with token refresh interceptor

---

Built with security-first principles for reliable study tracking.
