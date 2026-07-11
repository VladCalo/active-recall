# Active Recall Monitor

A production-ready, security-hardened web application for tracking study subjects using spaced repetition / active recall principles.

## Features

- **Secure Multi-User System**: Complete data isolation between users
- **Modern Authentication**: JWT with refresh token rotation and reuse detection
- **Strong Password Policies**: Minimum 12 characters, complexity requirements, common password blocking
- **Rate Limiting**: Redis-backed (with in-memory fallback) to prevent abuse
- **Calendar View**: Visual calendar showing upcoming review due dates with month/agenda views
- **Responsive UI**: Works on phones, tablets, and desktops
- **Kubernetes Native**: Deployed on k3s via ArgoCD GitOps ([k3s-rpi5](https://github.com/VladCalo/k3s-rpi5) repo)

## Quick Start

### Local Development

**Backend (Terminal 1):**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 7070
```

**Frontend (Terminal 2):**
```bash
cd frontend
npm install
npm run dev
```

Then open: **http://localhost:5173**

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│  PostgreSQL │
│  React/Vite │     │   FastAPI   │     └─────────────┘
│  Port 5173  │     │  Port 7070  │
└─────────────┘     └──────┬──────┘
                          │
                          ▼
                   ┌─────────────┐
                   │    Redis    │
                   │ (rate limit)│
                   └─────────────┘
```

## Pages

### Dashboard (`/`)
Shows today's reviews at a glance - subjects due for review today with their schedule information.

### Subjects (`/subjects`)
CRUD interface for managing your study subjects. Create subjects with a start date and choose between DEFAULT schedule (1, 3, 7, 14, 30, 60, 120, 180 days) or CUSTOM intervals.

### Calendar (`/calendar`)
Visual calendar showing all upcoming review due dates:

- **Month View**: Grid calendar with due subjects shown as color-coded badges on each day
- **Agenda View**: List view showing only days with reviews, sorted chronologically
- **Navigation**: Previous/next month buttons and "Today" quick-jump
- **Filtering**: Search box to filter by subject name
- **Day Details**: Click any day to see all subjects due in a popup dialog
- **Responsive**: Adapts to mobile (compact badges) and desktop (full view)

## Security Features

### Authentication & Authorization

| Feature | Implementation |
|---------|---------------|
| Password Hashing | Argon2 (64MB memory, 3 iterations) |
| Password Policy | Min 12 chars, uppercase, lowercase, number, special |
| Common Passwords | Blocked (configurable list) |
| Access Tokens | JWT, 15-minute expiry |
| Refresh Tokens | JWT in httpOnly cookie, 7-day expiry |
| Token Rotation | New refresh token on each use |
| Reuse Detection | Family-based revocation on reuse |
| Account Lockout | 5 failed attempts → 15 min lockout |

### Rate Limiting

| Endpoint | Limit |
|----------|-------|
| Login | 5 per 5 minutes per IP |
| Register | 3 per 10 minutes per IP |
| Token Refresh | 30 per minute per IP |
| API (general) | 120 per minute per user |

### Security Headers

All responses include:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy` (restricts browser features)
- `Strict-Transport-Security` (production only)
- `Content-Security-Policy` (production only)

### Data Protection

- User data isolation (queries scoped by user)
- Input validation with size limits
- Request body size limit (1MB)
- No stack traces in production errors
- Structured logging without secrets

## API Documentation

Interactive docs: **http://localhost:7070/docs**

### Auth Endpoints

```bash
# Get password requirements
curl http://localhost:7070/api/auth/password-requirements

# Register
curl -X POST http://localhost:7070/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecureP@ss123!"}'

# Login
curl -X POST http://localhost:7070/api/auth/login \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{"email": "user@example.com", "password": "SecureP@ss123!"}'

# Get current user (with token from login response)
curl http://localhost:7070/api/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Refresh token (uses httpOnly cookie)
curl -X POST http://localhost:7070/api/auth/refresh \
  -b cookies.txt

# Logout
curl -X POST http://localhost:7070/api/auth/logout \
  -b cookies.txt
```

### Subject Endpoints (requires auth)

```bash
# List subjects
curl http://localhost:7070/api/subjects \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Create subject
curl -X POST http://localhost:7070/api/subjects \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Cardiology", "start_date": "2026-01-25", "schedule_type": "DEFAULT"}'

# Today's reviews
curl "http://localhost:7070/api/reviews/today?tz=Europe/Bucharest" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Calendar range (for calendar view)
curl "http://localhost:7070/api/reviews/range?start=2026-01-01&end=2026-01-31&tz=Europe/Bucharest" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Testing

```bash
cd backend
source venv/bin/activate

# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_security.py -v
pytest tests/test_auth.py -v
pytest tests/test_user_isolation.py -v
```

## Production Deployment

This app is deployed to a k3s cluster via ArgoCD GitOps — see the [k3s-rpi5](https://github.com/VladCalo/k3s-rpi5)
repo (`apps/active-recall2/`) for the actual Kubernetes manifests (Postgres, Redis, backend, frontend,
HTTPRoute, ExternalSecret). There is no docker-compose or shell-script deployment path in this repo;
building images and pushing them to the in-cluster registry is the only supported flow.

### Security Checklist

Before deploying:

- [ ] **Generate secure secrets** for `JWT_SECRET_KEY` / `CSRF_SECRET_KEY` (stored in Vault, injected via ExternalSecret)
- [ ] **Set environment to production** (`ENVIRONMENT=production`, `DEBUG=false`)
- [ ] **Configure HTTPS cookies** (`COOKIE_SECURE=true`, `COOKIE_SAMESITE=strict`)
- [ ] **Lock down CORS** to the actual hostname
- [ ] **Use PostgreSQL** — `DATABASE_URL=postgresql://user:pass@host:5432/active_recall`
- [ ] **Deploy Redis** for distributed rate limiting

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | development | development/staging/production |
| `DEBUG` | false | Show detailed errors |
| `DATABASE_URL` | sqlite:///./app.db | Database connection string (Postgres in production) |
| `REDIS_URL` | - | Redis URL for rate limiting |
| `JWT_SECRET_KEY` | (random) | **REQUIRED in production** |
| `CSRF_SECRET_KEY` | (random) | **REQUIRED in production** |
| `COOKIE_SECURE` | false | true for HTTPS |
| `COOKIE_SAMESITE` | lax | lax or strict |
| `CORS_ORIGINS` | ["http://localhost:5173"] | Allowed origins |
| `MIN_PASSWORD_LENGTH` | 12 | Minimum password length |
| `RATE_LIMIT_LOGIN` | 5/5minute | Login rate limit |
| `RATE_LIMIT_REGISTER` | 3/10minute | Registration rate limit |

## Project Structure

```
active-recall/
├── backend/
│   ├── app/
│   │   ├── api/           # Route handlers
│   │   ├── core/          # Security, auth, logging
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic
│   │   ├── config.py      # Configuration
│   │   └── main.py        # FastAPI app
│   ├── alembic/           # Database migrations
│   ├── tests/             # Pytest tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── contexts/      # Auth context
│   │   ├── pages/         # Page components
│   │   └── lib/           # API client
│   └── package.json
└── README.md
```

## Development

### Code Style

- Backend: Python type hints, docstrings
- Frontend: TypeScript, ESLint
- Both: Meaningful variable names, no comments for obvious code

### Adding Features

1. Create/update model in `backend/app/models/`
2. Create migration: `alembic revision --autogenerate -m "description"`
3. Add Pydantic schema in `backend/app/schemas/`
4. Add business logic in `backend/app/services/`
5. Add API endpoint in `backend/app/api/`
6. Add tests in `backend/tests/`
7. Update frontend components

## License

MIT
