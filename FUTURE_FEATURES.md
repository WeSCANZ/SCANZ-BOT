# SCANZ-BOT Roadmap

## ✅ Implemented (Shipped)

- **GitHub Org Migration** — Repository lives at [WeSCANZ/SCANZ-BOT](https://github.com/WeSCANZ/SCANZ-BOT).
- **SQLite Persistence** — All state (verification links, reaction roles, suggestions config, enforcer config) stored in `data/*.db`. Survives restarts.
- **Secret Management** — All tokens/IDs sourced from `.env`. No hardcoded secrets in codebase.
- **RSI Verification System** — `/verify` bio checksum challenge links Discord accounts to RSI handles. Supports multiple orgs via `/add_org` / `/remove_org`.
- **Role Sync** — Automatically assigns Main Org, Affiliate, Guest, or Unverified roles based on live RSI org membership data after verification.
- **Roster Audit** — Weekly background task + manual `/roster_audit` and `/org_full_sync` to compare RSI rosters against the local database.
- **Message Enforcer** — Strict channel enforcement, formatted `/ping` posts, persistent subscription role buttons (`/scanz_subscriptions`), per-channel game loop configuration (`/scanz_format`).
- **Reaction Roles** — Persistent emoji-based role assignment via `/setup_reaction_role`.
- **Suggestions** — Anonymous or named submissions via `/suggestion`, staff reply DM notifications, configurable destination channel.
- **Admin Action Logging** — Key staff actions logged as embeds to `ADMIN_LOG_CHANNEL_ID`.
- **Welcome Messages** — New-member welcome embed posted to `WELCOME_CHANNEL_ID` on join.
- **Two-Instance Deployment** — Proxmox LXC setup with `main` (prod) and `dev` instances, GitHub webhook auto-deploy, `switch.sh` for manual branch switching.

---

## 🔮 Planned Features

### Near-Term

- [ ] **Member Nickname Sync** — Force Discord nicknames to match verified RSI handles after successful verification. Currently blocked by Discord permission restrictions in the LXC environment — needs investigation.
- [ ] **LFG Notifications** — Add a `[Remind Me]` button to `/ping` event embeds that DMs the user 15 minutes before the specified start time.
- [ ] **Dynamic LFG Voice Channels** — Temporary user-created voice channels tied to `/ping` events that auto-delete when empty.

### Medium-Term

- [ ] **Event Scheduling** — Automated Discord Event creation linked to the SCANZ website calendar.
- [ ] **Live Trade API Integration** — `/trade` command using [sc-trade.tools](https://sc-trade.tools) or similar to check commodity prices (Gold, RMC, etc.) at nearby locations.
- [ ] **Ship Encyclopedia** — `/ship` command scraping Erkul or RSI for live stats: max speed, cargo capacity, crew size, etc.

### Long-Term / Research

- [ ] **Fleet Management** — View org fleet readiness via integration with Fleetyards or an internal database.
- [ ] **SCANZ Bounty Board** — Bot acts as an internal ledger: members upload bounty/mining screenshots, bot assigns points and tracks reputation over time.

---

## Technical Reference: RSI Verification (Bio Checksum)

1. **Initiation** — User runs `/verify handle:RSI_HANDLE org:SCANZ`.
2. **Challenge** — Bot generates a unique code (e.g. `SCANZ-X9Y2`) tied to the user's Discord ID.
3. **User action** — User adds the code to their RSI Short Bio at [robertsspaceindustries.com/account/profile](https://robertsspaceindustries.com/account/profile).
4. **Verification** — Bot scrapes `https://robertsspaceindustries.com/citizens/{handle}`, confirms the code is present, links the account in `data/enforcer.db`, and syncs Discord roles.

## Technical Reference: Message Enforcer Channel Modes

1. **Strict** — All non-command messages deleted immediately; author DM'd a warning.
2. **Warn Only** — Messages flagged but not deleted; warning sent to channel.
3. **Timed Delete** — Messages deleted after a configurable delay.
4. **Grace Period** — New members are exempt for a configurable number of days.
