#!/bin/bash
# Update Active Recall on RPi5
# Run this after pushing changes to GitHub

set -e

APP_DIR="/mnt/ssd/github/active-recall"
ENV_FILE="/mnt/ssd/apps/active-recall/data/.env"
COMPOSE_FILE="docker-compose.prod.yml"

cd "$APP_DIR"

echo "==> Pulling latest code..."
git pull

echo "==> Stopping containers..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down

echo "==> Rebuilding..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build

echo "==> Starting..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d

echo "==> Done! Checking status..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps

echo ""
echo "Database preserved at: /mnt/ssd/apps/active-recall/data/db/"
