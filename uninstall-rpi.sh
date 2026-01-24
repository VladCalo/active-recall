#!/bin/bash
#
# Active Recall Monitor - Uninstall Script
#
# This script removes the service but PRESERVES your data by default.
# Use --delete-data to also remove the database.
#
# Usage:
#   sudo ./uninstall-rpi.sh              # Keep data
#   sudo ./uninstall-rpi.sh --delete-data # Delete everything
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

APP_NAME="active-recall"
DATA_DIR="/mnt/ssd/apps/active-recall/data"
APP_DIR="/mnt/ssd/github/active-recall"

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (sudo ./uninstall-rpi.sh)${NC}"
    exit 1
fi

echo -e "${YELLOW}Stopping service...${NC}"
systemctl stop ${APP_NAME}.service 2>/dev/null || true
systemctl disable ${APP_NAME}.service 2>/dev/null || true

echo -e "${YELLOW}Removing containers...${NC}"
cd "${APP_DIR}" 2>/dev/null && docker compose down --rmi local 2>/dev/null || true

echo -e "${YELLOW}Removing systemd service...${NC}"
rm -f /etc/systemd/system/${APP_NAME}.service
systemctl daemon-reload

echo -e "${YELLOW}Removing application files...${NC}"
# Don't remove APP_DIR if it's a git repo - just remove docker-compose.yml
rm -f "${APP_DIR}/docker-compose.yml"
rm -f "${DATA_DIR}/.env"

if [ "$1" == "--delete-data" ]; then
    echo -e "${RED}Removing ALL data (database, redis)...${NC}"
    rm -rf "${DATA_DIR}"
    echo -e "${GREEN}✓ All data deleted${NC}"
else
    echo -e "${GREEN}✓ Data preserved at ${DATA_DIR}${NC}"
    echo -e "  To delete data: sudo rm -rf ${DATA_DIR}"
fi

echo -e "\n${GREEN}Uninstall complete!${NC}"
