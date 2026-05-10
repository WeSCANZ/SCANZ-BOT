# SCANZ-BOT Server Deployment Guide

This guide covers provisioning the bot on a fresh Proxmox LXC container and managing the two-instance (prod/dev) deployment model.

---

## Architecture Overview

Two bot instances run on the same Proxmox host, each in its own directory (or LXC), each tracking a different git branch:

| Instance | Branch | Systemd Service | Port |
|---|---|---|---|
| Production | `main` | `scanz-bot` | 5000 (webhook) |
| Development | `dev` | `scanz-bot-dev` *(or separate LXC)* | 5001 (webhook) |

Each instance runs its own Flask webhook listener (`deploy/webhook_listener.py`). GitHub webhooks must be configured to POST to the correct instance's endpoint.

---

## 1. Initial Server Provisioning

### Prerequisites

- Proxmox LXC with Debian/Ubuntu
- Python 3.11+
- `git`, `systemd`

### Steps

```bash
# 1. Clone the repository
mkdir -p /opt/scanz-bot
cd /opt/scanz-bot
git clone https://github.com/WeSCANZ/SCANZ-BOT.git .

# 2. Create a virtual environment
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
nano .env   # Fill in DISCORD_TOKEN, GITHUB_SECRET, LOG_CHANNEL_ID, etc.

# 4. Make scripts executable
chmod +x update.sh deploy/switch.sh deploy/update.sh deploy/webhook_listener.py

# 5. Allow git in this directory (prevents root/LXC permission errors)
git config --global --add safe.directory /opt/scanz-bot
```

---

## 2. GitHub Authentication (Private Repo)

Since the repo is private, the server needs a deploy key to pull updates.

```bash
# Generate a deploy key (no passphrase)
ssh-keygen -t ed25519 -C "scanz-bot-server" -f ~/.ssh/scanz_bot_deploy -N ""

# Print the public key — add this to GitHub:
# Repo Settings → Deploy keys → Add deploy key (read-only is sufficient)
cat ~/.ssh/scanz_bot_deploy.pub

# Configure SSH to use this key for GitHub
cat >> ~/.ssh/config << EOF
Host github.com
    IdentityFile ~/.ssh/scanz_bot_deploy
    StrictHostKeyChecking no
EOF

# Update the remote to use SSH
cd /opt/scanz-bot
git remote set-url origin git@github.com:WeSCANZ/SCANZ-BOT.git
```

---

## 3. Systemd Services

### Discord Bot (`/etc/systemd/system/scanz-bot.service`)

```ini
[Unit]
Description=SCANZ Discord Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/scanz-bot
ExecStart=/opt/scanz-bot/venv/bin/python main.py
Restart=always
RestartSec=10
EnvironmentFile=/opt/scanz-bot/.env

[Install]
WantedBy=multi-user.target
```

### Webhook Listener (`/etc/systemd/system/scanz-bot-webhook.service`)

```ini
[Unit]
Description=SCANZ Bot GitHub Webhook Listener
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/scanz-bot
ExecStart=/opt/scanz-bot/venv/bin/python deploy/webhook_listener.py
Restart=always
RestartSec=10
EnvironmentFile=/opt/scanz-bot/.env

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start both services
systemctl daemon-reload
systemctl enable scanz-bot scanz-bot-webhook
systemctl start scanz-bot scanz-bot-webhook
```

---

## 4. GitHub Webhook Configuration

In the GitHub repository settings (**Settings → Webhooks → Add webhook**):

| Field | Value |
|---|---|
| Payload URL | `http://<server-ip>:5000/deploy` |
| Content type | `application/json` |
| Secret | Matches `GITHUB_SECRET` in `.env` |
| Events | **Just the push event** |

The webhook listener compares the pushed branch against the server's current git `HEAD`. Only matching pushes trigger a deployment — so prod and dev instances safely share the same webhook endpoint if on the same IP, or each have their own.

---

## 5. Branch Management

### Switch an instance to a different branch

```bash
bash /opt/scanz-bot/deploy/switch.sh dev   # switch to dev branch
bash /opt/scanz-bot/deploy/switch.sh main  # switch back to main
```

`switch.sh` checks out the target branch and immediately runs `update.sh` to apply it. All future webhook pushes to that branch will auto-deploy.

### Manual update (stay on current branch)

```bash
bash /opt/scanz-bot/update.sh
```

When called without an argument, `update.sh` reads the current git `HEAD` and deploys that branch.

---

## 6. Service Management Reference

```bash
# Status
sudo systemctl status scanz-bot
sudo systemctl status scanz-bot-webhook

# Restart
sudo systemctl restart scanz-bot
sudo systemctl restart scanz-bot-webhook

# Live logs
sudo journalctl -u scanz-bot -f
sudo journalctl -u scanz-bot-webhook -f
```

---

## 7. Branch Protection (GitHub)

Recommended settings under **Settings → Branches → Add rule → Pattern: `main`**:

- [x] Require a pull request before merging
- [x] Require at least 1 approval
- [x] Do not allow bypassing the above settings

All changes to `main` should go through a PR from `dev` or a feature branch.

---

## 8. Team Access

- **Settings → Collaborators** — Add authorised developers
- Developers workflow: `Clone → Create branch (feature/xyz) → Push → Open PR → Merge to dev → Test → Merge to main`
