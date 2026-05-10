# SCANZ-BOT

Discord bot for the **SCANZ** (Star Citizen Australia and New Zealand) org community.

**GitHub:** [WeSCANZ/SCANZ-BOT](https://github.com/WeSCANZ/SCANZ-BOT) (private) · **Discord:** [discord.gg/3atj8pjhFH](https://discord.gg/3atj8pjhFH) · **RSI Org:** [SCANZ](https://robertsspaceindustries.com/orgs/SCANZ)

## 📚 Documentation

- [Command Guide](COMMANDS.md) — Full list of available slash commands
- [Future Roadmap](FUTURE_FEATURES.md) — Planned features and research
- [Server Deployment](DEPLOYMENT.md) — Proxmox/LXC setup, webhook, branch management

---

## Local Setup

1. **Clone the repository:**
    ```bash
    git clone https://github.com/WeSCANZ/SCANZ-BOT.git
    cd SCANZ-BOT
    ```

2. **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    ```

3. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4. **Configure environment:**
    ```bash
    cp .env.example .env
    # Edit .env and fill in your values
    ```

5. **Run the bot:**
    ```bash
    python main.py
    ```

---

## Environment Variables

Copy `.env.example` → `.env` and fill in all required values. **Never commit `.env`.**

| Variable | Required | Description |
|---|---|---|
| `DISCORD_TOKEN` | ✅ | Bot token from the [Discord Developer Portal](https://discord.com/developers/applications) |
| `GITHUB_SECRET` | ✅ | HMAC secret used to authenticate GitHub webhook payloads |
| `LOG_CHANNEL_ID` | ✅ | Channel ID where the bot posts startup and update notifications |
| `ADMIN_LOG_CHANNEL_ID` | Optional | Channel ID for admin action audit log embeds |
| `WELCOME_CHANNEL_ID` | Optional | Channel ID where new-member welcome embeds are posted |

---

## Features

- **General & Utility** — `/hi`, `/latency`, `/time`, `/scanz_commands`, and `@SCANZ_BOT` keyword mention responses.
- **RSI Verification** — Link Discord accounts to RSI profiles via `/verify` (bio checksum challenge). Staff can manually link members (`/manual_verify`), search the database (`/search_verified`), export verified/unverified lists to CSV, and manage org symbols (`/add_org`, `/remove_org`).
- **Role Sync** — Automatically assigns Main, Affiliate, Guest, or Unverified roles based on RSI org membership status. Configurable via `/set_main_role`, `/set_affiliate_role`, `/set_guest_role`, `/set_unverified_role`.
- **Roster & Org Sync** — Weekly background audit of all verified members' org status via `/roster_audit`. Full RSI-vs-database comparison with `/org_full_sync`.
- **Message Enforcer** — Strict channel enforcement (non-command messages deleted) with `/enforce_channel`. Formatted ping/alert posts via `/ping` with automatic `@SCANZ` mention. Persistent subscription role buttons via `/scanz_subscriptions`.
- **Reaction Roles** — Assign roles by emoji reaction using `/setup_reaction_role`, with persistent state across restarts.
- **Suggestions** — Members submit feedback via `/suggestion` (with optional anonymity). Staff replies trigger a DM notification to the original author. Configurable destination channel.
- **Admin Action Logging** — Key staff actions (verifications, enforcer changes, roster audits) are logged as embeds to `ADMIN_LOG_CHANNEL_ID`.
- **Welcome Messages** — Sends a welcome embed to `WELCOME_CHANNEL_ID` when a new member joins.
- **System Notifications** — On startup the bot posts to `LOG_CHANNEL_ID` showing the current git branch and latest commit message.

---

## Deployment

The bot is deployed on a **Proxmox server** inside an LXC container, running as a `systemd` service. Two instances run side-by-side:

| Instance | Branch | Purpose |
|---|---|---|
| Production | `main` | Live bot, real Discord server |
| Development | `dev` | Testing and staging |

### Automatic Deployment (GitHub Webhook)

GitHub sends a push event → Flask webhook listener (`deploy/webhook_listener.py`, port 5000) → `update.sh`.

The listener reads the current git `HEAD` to decide which branch it's tracking, and ignores pushes to any other branch. This means each server instance auto-deploys only the branch it was last switched to.

### Manual Branch Switch

To manually switch an instance to a different branch:

```bash
bash /opt/scanz-bot/deploy/switch.sh dev   # switch to dev
bash /opt/scanz-bot/deploy/switch.sh main  # switch back to main
```

`switch.sh` checks out the target branch and immediately runs `update.sh` to deploy it.

### Manual Update (same branch)

```bash
bash /opt/scanz-bot/update.sh
```

When called without arguments, `update.sh` defaults to the currently checked-out branch (reads `git rev-parse --abbrev-ref HEAD`).

### Service Management

```bash
sudo systemctl status scanz-bot
sudo systemctl restart scanz-bot
sudo journalctl -u scanz-bot -f   # live logs
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for full server provisioning instructions.
