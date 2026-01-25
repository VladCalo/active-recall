#!/bin/bash
# Update Active Recall on RPi5
# Run this after pushing changes to GitHub

set -e

APP_DIR="/mnt/ssd/github/active-recall"
ENV_FILE="/mnt/ssd/apps/active-recall/data/.env"

cd "$APP_DIR"

git restore docker-compose.yml

echo "==> Pulling latest code..."
git pull

echo "==> Copying production compose file..."
cp docker-compose.prod.yml docker-compose.yml

echo "==> Stopping containers..."
docker compose --env-file "$ENV_FILE" down

echo "==> Rebuilding..."
docker compose --env-file "$ENV_FILE" build

echo "==> Starting..."
docker compose --env-file "$ENV_FILE" up -d

echo "==> Done!"
docker compose --env-file "$ENV_FILE" ps
