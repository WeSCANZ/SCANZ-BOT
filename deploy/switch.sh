#!/bin/bash
# Manual Branch Switcher (/opt/scanz-bot/switch.sh)

BOT_DIR="/opt/scanz-bot"
TARGET_BRANCH=$1

if [ -z "$TARGET_BRANCH" ]; then
    echo "Usage: ./switch.sh <branch_name>"
    echo "Example: ./switch.sh dev"
    exit 1
fi

echo "Switching server to track branch: $TARGET_BRANCH"
cd "$BOT_DIR" || exit 1

git fetch origin
git checkout "$TARGET_BRANCH"
git reset --hard "origin/$TARGET_BRANCH"

echo "Successfully switched. Running update script..."
/opt/scanz-bot/update.sh "$TARGET_BRANCH"
