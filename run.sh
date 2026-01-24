#!/bin/bash
# =============================================================================
# Active Recall Monitor - Local Development Runner
# =============================================================================
#
# This script runs both backend and frontend for local development.
#
# Usage:
#   ./run.sh          # Run both backend and frontend
#   ./run.sh backend  # Run only backend (port 7070)
#   ./run.sh frontend # Run only frontend (port 5173)
#   ./run.sh setup    # Initial setup (install dependencies)
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to print colored messages
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to setup the project
setup() {
    log_info "Setting up Active Recall Monitor..."
    
    # Backend setup
    log_info "Setting up backend..."
    cd "$PROJECT_ROOT/backend"
    
    if command_exists python3; then
        python3 -m venv venv
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        log_info "Backend dependencies installed"
    else
        log_error "Python 3 is required but not installed"
        exit 1
    fi
    
    # Frontend setup
    log_info "Setting up frontend..."
    cd "$PROJECT_ROOT/frontend"
    
    if command_exists npm; then
        npm install
        log_info "Frontend dependencies installed"
    else
        log_error "npm is required but not installed"
        exit 1
    fi
    
    log_info "Setup complete!"
    log_info "Run './run.sh' to start the application"
    log_info ""
    log_info "Default URLs:"
    log_info "  Backend:  http://localhost:7070"
    log_info "  Frontend: http://localhost:5173"
}

# Function to run the backend
run_backend() {
    log_info "Starting backend on port 7070..."
    cd "$PROJECT_ROOT/backend"
    
    # Activate virtual environment if it exists
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    # Run server on port 7070
    uvicorn app.main:app --reload --host 0.0.0.0 --port 7070
}

# Function to run the frontend
run_frontend() {
    log_info "Starting frontend on port 5173..."
    cd "$PROJECT_ROOT/frontend"
    npm run dev
}

# Function to run both services
run_all() {
    log_info "Starting Active Recall Monitor..."
    log_info "Backend:  http://localhost:7070"
    log_info "Frontend: http://localhost:5173"
    log_info "Press Ctrl+C to stop both services"
    
    # Run backend in background
    cd "$PROJECT_ROOT/backend"
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    uvicorn app.main:app --reload --host 0.0.0.0 --port 7070 &
    BACKEND_PID=$!
    
    # Run frontend in foreground
    cd "$PROJECT_ROOT/frontend"
    npm run dev &
    FRONTEND_PID=$!
    
    # Trap Ctrl+C to kill both processes
    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM
    
    # Wait for both processes
    wait
}

# Main script logic
case "${1:-all}" in
    setup)
        setup
        ;;
    backend)
        run_backend
        ;;
    frontend)
        run_frontend
        ;;
    all|"")
        run_all
        ;;
    *)
        echo "Usage: $0 {setup|backend|frontend|all}"
        exit 1
        ;;
esac
