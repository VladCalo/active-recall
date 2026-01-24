#!/bin/bash
#
# Active Recall Monitor - RPi5 Deployment Script
#
# This script:
# 1. Creates necessary directories for persistent storage
# 2. Generates secure secrets (if not already set)
# 3. Creates a systemd service for auto-start
# 4. Builds and starts Docker containers
#
# Usage:
#   sudo ./deploy-rpi.sh
#
# Data is stored in: /mnt/ssd/apps/active-recall/data
#   - /mnt/ssd/apps/active-recall/data/db/active-recall.db  (SQLite database)
#   - /mnt/ssd/apps/active-recall/data/redis/               (Redis persistence)
#
# App is stored in: /mnt/ssd/github/active-recall
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Active Recall Monitor - RPi5 Deployment${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (sudo ./deploy-rpi.sh)${NC}"
    exit 1
fi

# Configuration - CUSTOMIZE THESE PATHS
APP_NAME="active-recall"
DATA_DIR="/mnt/ssd/apps/active-recall/data"
APP_DIR="/mnt/ssd/github/active-recall"
ENV_FILE="${DATA_DIR}/.env"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "\n${YELLOW}Step 1: Creating directories...${NC}"
mkdir -p "${DATA_DIR}/db"
mkdir -p "${DATA_DIR}/redis"
mkdir -p "${APP_DIR}"

# Set permissions
chown -R 1000:1000 "${DATA_DIR}"
chmod -R 755 "${DATA_DIR}"

echo -e "${GREEN}✓ Data directories created at ${DATA_DIR}${NC}"

echo -e "\n${YELLOW}Step 2: Copying application files...${NC}"
# Copy files if script is run from a different location
if [ "${SCRIPT_DIR}" != "${APP_DIR}" ]; then
    cp -r "${SCRIPT_DIR}/backend" "${APP_DIR}/"
    cp -r "${SCRIPT_DIR}/frontend" "${APP_DIR}/"
    cp "${SCRIPT_DIR}/docker-compose.prod.yml" "${APP_DIR}/docker-compose.yml"
    echo -e "${GREEN}✓ Files copied to ${APP_DIR}${NC}"
else
    # If already in APP_DIR, just copy the docker-compose
    cp "${SCRIPT_DIR}/docker-compose.prod.yml" "${APP_DIR}/docker-compose.yml" 2>/dev/null || true
    echo -e "${GREEN}✓ Using files in ${APP_DIR}${NC}"
fi

echo -e "\n${YELLOW}Step 3: Setting up environment...${NC}"

# Generate secrets if .env doesn't exist or secrets are missing
if [ ! -f "${ENV_FILE}" ]; then
    echo "Generating new secrets..."
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))" 2>/dev/null || openssl rand -base64 48)
    CSRF_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || openssl rand -base64 24)
    
    cat > "${ENV_FILE}" << EOF
# Active Recall Monitor - Production Environment
# Generated on $(date)

# Security Keys (DO NOT SHARE)
JWT_SECRET_KEY=${JWT_SECRET}
CSRF_SECRET_KEY=${CSRF_SECRET}

# Data directory
DATA_DIR=${DATA_DIR}

# Cookie settings (set to true if using HTTPS)
COOKIE_SECURE=false

# CORS - Add your RPi's IP/hostname here
# Example: CORS_ORIGINS=["http://192.168.1.100","http://raspberrypi.local"]
CORS_ORIGINS=["http://localhost","http://127.0.0.1"]
EOF
    
    chmod 600 "${ENV_FILE}"
    echo -e "${GREEN}✓ Environment file created at ${ENV_FILE}${NC}"
    echo -e "${YELLOW}  IMPORTANT: Edit ${ENV_FILE} to add your RPi's IP to CORS_ORIGINS${NC}"
else
    echo -e "${GREEN}✓ Environment file already exists${NC}"
fi

echo -e "\n${YELLOW}Step 4: Creating systemd service...${NC}"

cat > /etc/systemd/system/${APP_NAME}.service << EOF
[Unit]
Description=Active Recall Monitor
Documentation=https://github.com/your/active-recall
After=docker.service network-online.target
Requires=docker.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${APP_DIR}
EnvironmentFile=${ENV_FILE}
ExecStartPre=/usr/bin/docker compose pull --ignore-pull-failures
ExecStart=/usr/bin/docker compose up -d --build --remove-orphans
ExecStop=/usr/bin/docker compose down
ExecReload=/usr/bin/docker compose up -d --build
TimeoutStartSec=300
TimeoutStopSec=60

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

echo -e "${GREEN}✓ Systemd service created${NC}"

echo -e "\n${YELLOW}Step 5: Building and starting containers...${NC}"

cd "${APP_DIR}"

# Source environment
set -a
source "${ENV_FILE}"
set +a

# Build and start
docker compose build
docker compose up -d

echo -e "${GREEN}✓ Containers started${NC}"

echo -e "\n${YELLOW}Step 6: Enabling auto-start on boot...${NC}"
systemctl enable ${APP_NAME}.service
echo -e "${GREEN}✓ Service enabled${NC}"

# Get IP address
IP_ADDR=$(hostname -I | awk '{print $1}')

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e ""
echo -e "Access your app at:"
echo -e "  ${GREEN}http://${IP_ADDR}${NC}"
echo -e "  ${GREEN}http://$(hostname).local${NC} (if mDNS is enabled)"
echo -e ""
echo -e "Data stored at:"
echo -e "  Database: ${DATA_DIR}/db/active-recall.db"
echo -e "  Redis:    ${DATA_DIR}/redis/"
echo -e ""
echo -e "Service commands:"
echo -e "  ${YELLOW}sudo systemctl status ${APP_NAME}${NC}  - Check status"
echo -e "  ${YELLOW}sudo systemctl restart ${APP_NAME}${NC} - Restart"
echo -e "  ${YELLOW}sudo systemctl stop ${APP_NAME}${NC}    - Stop"
echo -e "  ${YELLOW}sudo journalctl -u ${APP_NAME} -f${NC}  - View logs"
echo -e ""
echo -e "Docker commands:"
echo -e "  ${YELLOW}cd ${APP_DIR} && docker compose logs -f${NC} - View container logs"
echo -e "  ${YELLOW}cd ${APP_DIR} && docker compose ps${NC}      - Container status"
echo -e ""
echo -e "${YELLOW}IMPORTANT:${NC}"
echo -e "  Edit ${ENV_FILE} to add your network IP to CORS_ORIGINS"
echo -e "  Example: CORS_ORIGINS=[\"http://${IP_ADDR}\",\"http://$(hostname).local\"]"
echo -e "  Then run: ${YELLOW}sudo systemctl restart ${APP_NAME}${NC}"
