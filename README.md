# Active Recall Monitor

A production-quality web application for tracking study subjects and generating daily review schedules using spaced repetition / active recall principles.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Quick Start](#quick-start)
  - [Manual Setup](#manual-setup)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Deployment](#deployment)
- [Code Walkthrough](#code-walkthrough)
- [Contributing](#contributing)

## Overview

Active Recall Monitor helps you implement spaced repetition for your studies. You add subjects (e.g., "Cardiology", "Pharmacology"), set a start date, and the app automatically calculates when each subject needs to be reviewed based on optimal memory retention intervals.

The default interval schedule is: **1, 3, 7, 14, 30, 60, 120, 180 days** — based on proven spaced repetition research. You can also create custom schedules.

## Features

- **Dashboard**: Shows subjects due for review today (based on Europe/Bucharest timezone)
- **Subject Management**: Add, edit, and delete study subjects
- **Flexible Scheduling**: Use default intervals or create custom review schedules
- **Next Due Calculation**: See when each subject needs to be reviewed next
- **Beautiful UI**: Modern, responsive design with shadcn/ui components
- **API Documentation**: Interactive Swagger docs at `/docs`

## Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│                 │      │                 │      │                 │
│  React Frontend │◄────►│  FastAPI Backend│◄────►│  SQLite DB      │
│  (Vite + TS)    │ HTTP │  (Python 3.11)  │      │  (SQLAlchemy)   │
│                 │      │                 │      │                 │
└─────────────────┘      └─────────────────┘      └─────────────────┘
     Port 5173                Port 8000              app.db file
```

### Data Flow

1. User opens the Dashboard
2. Frontend calls `GET /api/reviews/today?tz=Europe/Bucharest`
3. Backend computes today's date in the specified timezone
4. Backend queries all subjects and computes due dates
5. Subjects where `start_date + interval == today` are returned
6. Frontend displays the review cards

## Tech Stack

### Backend
- **Python 3.11** - Modern Python with type hints
- **FastAPI** - High-performance async API framework
- **Uvicorn** - ASGI server
- **SQLAlchemy 2.0** - ORM with modern type annotations
- **Alembic** - Database migrations
- **Pydantic** - Data validation
- **Pytest** - Testing framework

### Frontend
- **React 18** - UI library
- **TypeScript** - Type-safe JavaScript
- **Vite** - Fast build tool
- **TailwindCSS** - Utility-first CSS
- **shadcn/ui** - Beautiful UI components
- **Lucide React** - Icon library
- **Axios** - HTTP client
- **React Router** - Client-side routing

## Project Structure

```
active-recall/
├── backend/                    # Python FastAPI application
│   ├── app/
│   │   ├── api/               # API route handlers
│   │   │   ├── health.py      # Health check endpoint
│   │   │   ├── subjects.py    # Subject CRUD endpoints
│   │   │   └── reviews.py     # Review query endpoints
│   │   ├── models/            # SQLAlchemy ORM models
│   │   │   └── subject.py     # Subject model with ScheduleType enum
│   │   ├── schemas/           # Pydantic validation schemas
│   │   │   ├── subject.py     # Subject request/response schemas
│   │   │   └── review.py      # Review response schemas
│   │   ├── services/          # Business logic layer
│   │   │   ├── subject_service.py  # Subject CRUD operations
│   │   │   └── review_service.py   # Due date calculations
│   │   ├── config.py          # Configuration management
│   │   ├── database.py        # Database setup
│   │   └── main.py            # FastAPI application entry
│   ├── alembic/               # Database migrations
│   ├── tests/                 # Pytest test suite
│   ├── requirements.txt       # Python dependencies
│   ├── seed.py               # Sample data script
│   └── Dockerfile            # Backend container
│
├── frontend/                  # React application
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/           # shadcn/ui components
│   │   │   ├── Layout.tsx    # Main layout with nav
│   │   │   └── SubjectDialog.tsx  # Add/edit modal
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx # Today's reviews page
│   │   │   └── Subjects.tsx  # Subject management page
│   │   ├── hooks/
│   │   │   └── use-toast.ts  # Toast notification hook
│   │   ├── lib/
│   │   │   ├── api.ts        # API client functions
│   │   │   └── utils.ts      # Utility functions
│   │   ├── App.tsx           # Root component with routing
│   │   ├── main.tsx          # Entry point
│   │   └── index.css         # Global styles
│   ├── package.json          # Node dependencies
│   └── Dockerfile            # Frontend container
│
├── docker-compose.yml        # Container orchestration
├── run.sh                    # Development runner script
└── README.md                 # This file
```

## Getting Started

### Prerequisites

- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **npm** - Comes with Node.js

### Quick Start

The fastest way to get running:

```bash
# Clone the repository (if needed)
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
- **Backend API docs**: http://localhost:8000/docs

### Manual Setup

If you prefer manual setup:

#### Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server (tables created automatically)
uvicorn app.main:app --reload --port 8000
```

#### Frontend Setup

```bash
# Navigate to frontend
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
./run.sh           # Runs both backend and frontend
./run.sh backend   # Runs only backend
./run.sh frontend  # Runs only frontend
```

**Option 2: Manual (two terminals)**

Terminal 1 - Backend:
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Terminal 2 - Frontend:
```bash
cd frontend
npm run dev
```

### Production Mode (Docker)

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

### Seeding Sample Data

```bash
cd backend
source venv/bin/activate
python seed.py
```

## API Documentation

Interactive API documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/subjects` | List all subjects |
| POST | `/api/subjects` | Create a subject |
| GET | `/api/subjects/{id}` | Get a subject |
| PUT | `/api/subjects/{id}` | Update a subject |
| DELETE | `/api/subjects/{id}` | Delete a subject |
| GET | `/api/reviews/today?tz=Europe/Bucharest` | Get today's reviews |
| GET | `/api/reviews/upcoming?days=7` | Get upcoming reviews |

### Sample cURL Commands

```bash
# Health check
curl http://localhost:8000/api/health

# Create a subject
curl -X POST http://localhost:8000/api/subjects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Cardiology",
    "start_date": "2026-01-25",
    "schedule_type": "DEFAULT"
  }'

# Create a subject with custom schedule
curl -X POST http://localhost:8000/api/subjects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Anatomy",
    "start_date": "2026-01-25",
    "schedule_type": "CUSTOM",
    "custom_intervals_days": [1, 2, 4, 7, 14, 28]
  }'

# List all subjects
curl http://localhost:8000/api/subjects

# Get today's reviews
curl "http://localhost:8000/api/reviews/today?tz=Europe/Bucharest"

# Get upcoming reviews for 14 days
curl "http://localhost:8000/api/reviews/upcoming?days=14&tz=Europe/Bucharest"

# Update a subject
curl -X PUT http://localhost:8000/api/subjects/{id} \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Cardiology Updated"
  }'

# Delete a subject
curl -X DELETE http://localhost:8000/api/subjects/{id}
```

## Testing

### Backend Tests

```bash
cd backend
source venv/bin/activate

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_review_service.py

# Run with coverage
pytest --cov=app
```

### Frontend Lint

```bash
cd frontend
npm run lint
npm run build  # Type check + build
```

## Deployment

### Docker on Raspberry Pi 5

The Docker images are built for multi-arch support (amd64, arm64).

```bash
# On your RPi5
git clone <repo-url>
cd active-recall

# Build and run
docker-compose up -d --build

# Access at http://<rpi-ip>:5173
```

### Switching to PostgreSQL

1. Update `backend/.env`:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/active_recall
```

2. Install psycopg2:
```bash
pip install psycopg2-binary
```

3. Update `backend/app/database.py` to remove SQLite-specific config:
```python
# Remove: connect_args={"check_same_thread": False}
engine = create_engine(settings.database_url)
```

4. Run migrations:
```bash
alembic upgrade head
```

## Code Walkthrough

### For New Developers

Here's how to understand the codebase:

#### Backend Architecture

1. **Entry Point**: `backend/app/main.py`
   - Creates FastAPI app
   - Configures CORS
   - Includes routers

2. **Configuration**: `backend/app/config.py`
   - Uses pydantic-settings for type-safe config
   - Loads from environment variables

3. **Database**: `backend/app/database.py`
   - SQLAlchemy engine and session setup
   - `get_db()` dependency for FastAPI routes

4. **Models**: `backend/app/models/subject.py`
   - SQLAlchemy ORM model
   - `ScheduleType` enum (DEFAULT, CUSTOM)

5. **Schemas**: `backend/app/schemas/`
   - Pydantic models for request/response validation
   - `SubjectCreate`, `SubjectUpdate`, `SubjectResponse`

6. **Services**: `backend/app/services/`
   - Business logic separate from routes
   - `SubjectService`: CRUD operations
   - `ReviewService`: Due date calculations

7. **API Routes**: `backend/app/api/`
   - REST endpoints
   - Dependency injection for services

#### Frontend Architecture

1. **Entry Point**: `frontend/src/main.tsx`
   - React DOM render
   - Router setup

2. **App Component**: `frontend/src/App.tsx`
   - Route definitions
   - Layout wrapper

3. **Pages**: `frontend/src/pages/`
   - `Dashboard.tsx`: Today's reviews
   - `Subjects.tsx`: CRUD interface

4. **Components**: `frontend/src/components/`
   - `Layout.tsx`: Navigation header
   - `SubjectDialog.tsx`: Add/edit modal
   - `ui/`: shadcn/ui components

5. **API Client**: `frontend/src/lib/api.ts`
   - Typed API functions
   - Axios configuration

#### Key Concepts

**Due Date Calculation** (in `ReviewService`):
```python
def compute_due_dates(self, subject):
    # For each interval, add it to the start date
    # Example: start=Jan 25, interval=3 → due=Jan 28
    due_dates = []
    for interval in self.get_intervals(subject):
        due_date = subject.start_date + timedelta(days=interval)
        due_dates.append(due_date)
    return sorted(due_dates)
```

**Timezone Handling**:
```python
def get_today(self, timezone):
    # Always compute "today" in the user's timezone
    tz = ZoneInfo(timezone)
    return datetime.now(tz).date()
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests: `pytest` and `npm run lint`
5. Commit: `git commit -m 'Add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Open a Pull Request

---

Built with care for effective learning through spaced repetition.
