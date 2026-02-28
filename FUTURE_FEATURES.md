# SCANZ-BOT Roadmap

## Phase 1: Stability & Security (Current)
**Goal**: Establish a solid foundation for development and deployment.
- [x] **Migration**: Move the project to the [WeSCANZ](https://github.com/WeSCANZ/SCANZ-BOT) GitHub organization.
- [/] **Persistence**: Implement database storage (SQLite) for the `ReactionRoles` cog to prevent data loss on bot restart.
- [/] **Secret Management**: Audit all files for hardcoded IDs/Tokens and ensure `.env` consistency (Ongoing).
- [ ] **Message Enforcer**: Strict channel formatting for Ping/LFG channels using slash commands.

## Phase 2: Core Utility (Q1 2026)
**Goal**: Implement essential SCANZ-specific automation.
- [x] **RSI Verification System**: Link Discord handles to RSI accounts via the "Bio Checksum" method.
    - [x] Research `beautifulsoup4` performance for RSI profile scraping.
    - [x] Implement `/verify` challenge logic.
- [ ] **Member Nickname Sync**: Force Discord nicknames to match verified RSI handles.
- [ ] **Role Sync**: Automatically assign "Verified" and "Member" roles based on RSI Org data.

## Phase 3: Advanced Features (Q2 2026+)
**Goal**: Integration and enforcement.
- [ ] **Fleet Management**: Command to view org fleet readiness (integration with Fleetyards or internal DB).
- [ ] **Event Scheduling**: Automated Discord Event creation linked to the SCANZ website.
- [ ] **Automated Roster Sweeping**: Cron job to scrape SCANZ RSI Org roster and strip Discord roles from departed members.
- [ ] **Dynamic LFG Voice Channels**: Temporary user-created voice channels tied directly to `/post` events that auto-delete when empty.
- [ ] **LFG Notifications**: Add a `[Remind Me]` clickable button to event embeds to DM users 15 minutes before the start time.
- [ ] **Live Trade API Integration**: Integrations with sc-trade.tools or similar for `/trade` command to check local commodity prices like Gold/RMC.
- [ ] **Ship Encyclopedia**: Implement a `!ship` command scraping Erkul or RSI for live stats on Max Speed, Cargo, Crew Size, etc.
- [ ] **SCANZ Bounty Board**: Bot acts as an internal ledger tracking screenshot uploads of bounties/mining goals, assigning points/reputation.

---

## Technical Details: RSI Verification (The "Bio Checksum")
1.  **User Initiation**: User runs `/verify handle:[RSI_HANDLE]`.
2.  **Challenge Generation**: Bot generates a unique 6-character code (e.g., `SCANZ-X9Y2`) and links it to the User ID.
3.  **User Action**: User adds the code to their RSI Bio at [robertsspaceindustries.com/account/profile](https://robertsspaceindustries.com/account/profile).
4.  **Verification**: Bot scrapes `https://robertsspaceindustries.com/citizens/{handle}`, checks for the code, and syncs data to Discord and the SCANZ Roster (Google Sheets).

## Technical Details: Strict Channel Formatting
1.  **Monitor**: Watch designated channels.
2.  **Validate**: Users must use `/post type:LFG ...`.
3.  **Action**: Delete manual messages and provide a private ephemeral guide.


