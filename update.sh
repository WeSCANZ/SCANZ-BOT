#!/bin/bash
# Server-side Deployment Script (/opt/scanz-bot/update.sh)

BOT_DIR="/opt/scanz-bot"
SERVICE_NAME="scanz-bot"

# Branch is passed from the webhook listener, or fall back to current git HEAD
CURRENT_BRANCH=${1:-$(git -C "$BOT_DIR" rev-parse --abbrev-ref HEAD)}

echo "Starting deployment for branch: $CURRENT_BRANCH"
cd "$BOT_DIR" || exit 1

# Setup Safe Directory to prevent root/git permission errors in LXC
git config --global --add safe.directory "$BOT_DIR"

# Ensure script is executable for future runs
chmod +x update.sh deploy/switch.sh deploy/update.sh 2>/dev/null || true

# Hard Reset to match origin branch
git fetch origin
git checkout "$CURRENT_BRANCH"
git reset --hard origin/$CURRENT_BRANCH

# Application Updates
./venv/bin/pip install -r requirements.txt

# Service Restart
systemctl restart "$SERVICE_NAME"
echo "Deployment complete for branch: $CURRENT_BRANCH"
