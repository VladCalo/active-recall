# Active Recall Monitor

A production-ready, security-hardened web application for tracking study subjects using spaced repetition / active recall principles.

## Features

- **Secure Multi-User System**: Complete data isolation between users
- **Modern Authentication**: JWT with refresh token rotation and reuse detection
- **Strong Password Policies**: Minimum 12 characters, complexity requirements, common password blocking
- **Rate Limiting**: Redis-backed (with in-memory fallback) to prevent abuse
- **Responsive UI**: Works on phones, tablets, and desktops
- **Production Ready**: Docker Compose deployment with health checks

## Quick Start

### One-Command Local Development

```bash
# Install dependencies (first time only)
./run.sh setup

# Start everything (backend on 7070, frontend on 5173)
./run.sh
```

Then open: **http://localhost:5173**

### Manual Setup

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

### Docker Compose

```bash
# Generate required secrets
export JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
export CSRF_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Start all services
docker-compose up --build
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│   SQLite    │
│  React/Vite │     │   FastAPI   │     │  (or PG)    │
│  Port 5173  │     │  Port 7070  │     └─────────────┘
└─────────────┘     └──────┬──────┘
                          │
                          ▼
                   ┌─────────────┐
                   │    Redis    │
                   │ (rate limit)│
                   └─────────────┘
```

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

### Security Checklist

Before deploying to production:

- [ ] **Generate secure secrets**
  ```bash
  export JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
  export CSRF_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
  ```

- [ ] **Set environment to production**
  ```bash
  export ENVIRONMENT=production
  export DEBUG=false
  ```

- [ ] **Configure HTTPS cookies**
  ```bash
  export COOKIE_SECURE=true
  export COOKIE_SAMESITE=strict  # or lax
  ```

- [ ] **Lock down CORS**
  ```bash
  export CORS_ORIGINS='["https://yourdomain.com"]'
  ```

- [ ] **Use PostgreSQL** (recommended for production)
  ```bash
  export DATABASE_URL="postgresql://user:pass@host:5432/active_recall"
  ```

- [ ] **Deploy Redis** for distributed rate limiting

- [ ] **Use reverse proxy** (nginx/caddy) with HTTPS

- [ ] **Set up monitoring** for auth failure events

### Docker Production Deployment

```bash
# Create .env file with production values
cat > .env << 'EOF'
ENVIRONMENT=production
DEBUG=false
JWT_SECRET_KEY=your-64-char-secret-here
CSRF_SECRET_KEY=your-32-char-secret-here
COOKIE_SECURE=true
COOKIE_SAMESITE=strict
CORS_ORIGINS=["https://yourdomain.com"]
EOF

# Deploy
docker-compose up -d
```

### Nginx Configuration (HTTPS)

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Frontend
    location / {
        proxy_pass http://localhost:5173;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:7070;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Raspberry Pi 5 Deployment (Recommended)

One-command deployment with auto-start on boot:

```bash
# SSH to your Pi
ssh pi@your-pi-ip

# Clone the repo
git clone https://github.com/your/active-recall.git
cd active-recall

# Run the deployment script (does everything)
sudo ./deploy-rpi.sh
```

**What the script does:**
1. Creates data directories at `/mnt/ssd/apps/active-recall/data/`
2. Generates secure secrets automatically
3. Builds and starts Docker containers
4. Creates a systemd service for auto-start on boot
5. Stores database at `/mnt/ssd/apps/active-recall/data/db/active-recall.db`

**After deployment:**
```bash
# Edit CORS to allow access from your network
sudo nano /mnt/ssd/apps/active-recall/data/.env

# Add your Pi's IP to CORS_ORIGINS:
# CORS_ORIGINS=["http://192.168.1.100","http://raspberrypi.local"]

# Restart to apply
sudo systemctl restart active-recall
```

**Service commands:**
```bash
sudo systemctl status active-recall   # Check status
sudo systemctl restart active-recall  # Restart
sudo systemctl stop active-recall     # Stop
sudo journalctl -u active-recall -f   # View logs
```

**Data location:**
- Database: `/mnt/ssd/apps/active-recall/data/db/active-recall.db`
- Redis: `/mnt/ssd/apps/active-recall/data/redis/`
- Config: `/mnt/ssd/apps/active-recall/data/.env`
- App: `/mnt/ssd/github/active-recall/`

**Backup your data:**
```bash
# Backup database
sudo cp /mnt/ssd/apps/active-recall/data/db/active-recall.db ~/backup-$(date +%Y%m%d).db
```

**Uninstall:**
```bash
sudo ./uninstall-rpi.sh              # Keeps your data
sudo ./uninstall-rpi.sh --delete-data # Deletes everything
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | development | development/staging/production |
| `DEBUG` | false | Show detailed errors |
| `DATABASE_URL` | sqlite:///./app.db | Database connection string |
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
├── docker-compose.yml
├── run.sh
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
