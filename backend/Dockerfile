# Active Recall Monitor - Backend Dockerfile
# Multi-stage build for smaller production image
# Works on ARM64 (RPi5) and AMD64

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies (including for argon2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# Stage 2: Production
FROM python:3.11-slim as production

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set PYTHONPATH so alembic can find app module
ENV PYTHONPATH="/app:$PYTHONPATH"

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port 7070
EXPOSE 7070

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7070/api/health')"

# Run the application on port 7070
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7070"]
