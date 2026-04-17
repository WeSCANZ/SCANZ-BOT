#!/bin/bash
BOT_DIR="/opt/scanz-bot"
SERVICE_NAME="scanz-bot"

echo "Starting deployment..."
cd "$BOT_DIR" || exit 1
git fetch origin
git reset --hard origin/main
# Update dependencies if they changed
./venv/bin/pip install -r requirements.txt
# Restart the bot
systemctl restart "$SERVICE_NAME"
echo "Deployment complete."
