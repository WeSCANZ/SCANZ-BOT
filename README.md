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
    Copy `.env.example` to `.env` and fill in your values:
    ```bash
    cp .env.example .env
    ```

5.  **Run the bot:**
    ```bash
    python main.py
    ```

## Features
- **General**: `!hi`, `!ping`, `!time`, `/scanz_commands`, and `@SCANZ_BOT` keyword mentions.
- **RSI Verification**: Link Discord accounts to Roberts Space Industries profiles using `/verify` and profile bio checksums.
- **Message Enforcer**: Slash-command based LFG/LFM/EVENT posts with channel enforcement and automatic role-based pings.
- **Role Subscriptions**: Interactive button-based system for members to subscribe to specific activity pings.
