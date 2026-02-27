#!/bin/bash
# Manual Branch Switcher (/opt/discord-bots/switch.sh)

BOT_DIR="/opt/discord-bots/my-bot"
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
/opt/discord-bots/update.sh "$TARGET_BRANCH"
