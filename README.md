# SCANZ-BOT

Development repository for the SCANZ Star Citizen Org Discord Bot.

## 📚 Documentation
- [Command Guide](COMMANDS.md) - Full list of available commands.
- [Future Roadmap](FUTURE_FEATURES.md) - Planned features and research.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/WeSCANZ/SCANZ-BOT.git
    cd SCANZ-BOT
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment:**
    Copy `.env.example` to `.env` and fill in your values (including `DISCORD_TOKEN` and `LOG_CHANNEL_ID`):
    ```bash
    cp .env.example .env
    ```

5.  **Run the bot:**
    ```bash
    python main.py
    ```

## Features
- **General**: `/hi`, `/latency`, `/time`, `/scanz_commands`, and `@SCANZ_BOT` keyword mention responses.
- **RSI Verification**: Link Discord accounts to RSI profiles via `/verify` (bio checksum challenge). Staff can manually link members (`/manual_verify`), search the database (`/search_verified`), export verified/unverified lists to CSV, and manage org symbols (`/add_org`, `/remove_org`).
- **Role Sync**: Automatically assigns Main, Affiliate, Guest, or Unverified roles based on RSI org membership status. Configurable via `/set_main_role`, `/set_affiliate_role`, `/set_guest_role`, `/set_unverified_role`.
- **Roster & Org Sync**: Weekly background audit of all verified members' org status via `/roster_audit`. Full RSI-vs-database comparison with `/org_full_sync`.
- **Message Enforcer**: Strict channel enforcement (non-command messages deleted) with `/enforce_channel`. Formatted ping/alert posts via `/ping` with automatic `@SCANZ` mention. Persistent subscription role buttons via `/scanz_subscriptions`.
- **Reaction Roles**: Assign roles by emoji reaction using `/setup_reaction_role`, with persistent state across restarts.
- **Suggestions**: Members submit feedback via `/suggestion` (with optional anonymity). Staff replies trigger a DM notification to the original author. Configurable destination channel.
- **System Notifications**: Automatic startup alert sent to `LOG_CHANNEL_ID` showing the current git branch and latest commit message.