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
- **General**: `!hi`, `!ping`, `!time`, `/scanz_commands`, and `@SCANZ_BOT` keyword mentions.
- **RSI Verification**: Link Discord accounts to Roberts Space Industries profiles using `/verify`. Admins can manually link members via `/manual_verify`, search the database with `/search_verified`, or export data to CSV with `/export_verified`.
- **Roster & Org Sync**: Monitor organization membership with `/roster_audit` and perform full synchronization checks against the RSI website using `/org_full_sync`.
- **Message Enforcer**: Slash-command based LFG/LFM/EVENT posts with channel enforcement and automatic role-based pings.
- **System Notifications**: Automatic reboot and update alerts sent to a designated log channel, including git branch and commit info.