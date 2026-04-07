# SCANZ-BOT Command Guide

This document lists all available slash commands for the SCANZ-BOT.

> **Permission levels:**
> - **Everyone** — Any server member.
> - **Staff or Admin** — Members with the configured staff role OR Administrator permission.
> - **Admin only** — Requires the Discord *Administrator* permission.

---

## General & Utility

| Command | Description | Permission |
|---------|-------------|------------|
| `/hi` | Says hello with a random, personalised message. | Everyone |
| `/latency` | Checks the bot's WebSocket latency. | Everyone |
| `/time` | Displays current time across SCANZ timezones (ICT, AWST, AET, NZT). | Everyone |
| `/scanz_commands` | Shows a full list of available commands in an ephemeral embed. | Everyone |

**`@SCANZ_BOT` mentions** — Mentioning the bot in any channel triggers keyword-aware responses (e.g. `website`, `discord`, `org`, `help`) with fallback witty replies.

---

## Suggestions

| Command | Description | Permission |
|---------|-------------|------------|
| `/suggestion text: [anonymous:]` | Submit feedback or an idea to staff. Set `anonymous:True` to hide your name. | Everyone |
| `/set_suggestion_channel channel:` | Set the destination channel for incoming suggestions. | Staff or Admin |

---

## Message Enforcer & Pings

| Command | Description | Permission |
|---------|-------------|------------|
| `/ping game_loop: description: [time:] [location:] [requirements:] [link:] [channel:]` | Create a formatted alert/ping. Automatically mentions `@SCANZ`. Posts to the configured ping channel or the specified `channel`. | Everyone |
| `/enforce_channel mode: [parameters:]` | Configure message enforcement for the current channel. Modes: `Strict`, `Warn Only`, `Timed Delete`, `Grace Period`. | Staff or Admin |
| `/enforcer_user_reminder user: message: [punishment_type:] [punishment_value:]` | Set a custom reminder and optional punishment (e.g. timeout) for a specific user. | Staff or Admin |
| `/scanz_format` | Interactive setup for a channel's allowed Game Loops. Posts an informational embed on save. Channel must be enforced first. | Staff or Admin |
| `/set_ping_target channel:` | Set the default destination channel for `/ping` posts. | Staff or Admin |
| `/scanz_subscriptions` | Post a persistent role-subscription message with toggle buttons. | Staff or Admin |

---

## RSI Verification

### Member Commands

| Command | Description | Permission |
|---------|-------------|------------|
| `/verify handle: [org:]` | Link your Discord account to your RSI Handle via a bio checksum challenge. Autocomplete available for `org`. | Everyone |
| `/list_orgs` | List all configured RSI organisation/affiliate symbols. | Everyone |

### Staff Commands

| Command | Description | Permission |
|---------|-------------|------------|
| `/manual_verify member: handle: [org:]` | Initiate a checksum verification on behalf of a member. | Staff or Admin |
| `/grant_verified member:` | Manually apply the correct verified role to an already-linked member. | Staff or Admin |
| `/search_verified query:` | Search the verification database by RSI handle, Discord ID, or mention. | Staff or Admin |
| `/export_verified` | Export all verified members to a CSV file. | Staff or Admin |
| `/export_unverified [role:]` | Export members without a verification link to a CSV file. Optionally filter by role. | Staff or Admin |
| `/add_org symbol:` | Add an RSI organisation or affiliate symbol to the configuration. | Staff or Admin |
| `/remove_org symbol:` | Remove an RSI organisation or affiliate symbol. | Staff or Admin |

### Role Configuration

| Command | Description | Permission |
|---------|-------------|------------|
| `/set_main_role role:` | Set the role granted to verified **Main Org** members. | Staff or Admin |
| `/set_affiliate_role role:` | Set the role granted to verified **Affiliate** members. | Staff or Admin |
| `/set_guest_role role:` | Set the role granted to verified **Honored Guests** (non-org verified users). | Staff or Admin |
| `/set_unverified_role role:` | Set the role applied to unverified members (e.g. *Needs Verification*). | Staff or Admin |
| `/set_scanz_role role:` | Set the optional "SCANZ identifier" role used to scope unverified checks. | Staff or Admin |

### Admin-Only Configuration

| Command | Description | Permission |
|---------|-------------|------------|
| `/set_staff_role role:` | Set the role that can use all staff commands. | Admin only |
| `/set_log_channel channel:` | Set the channel for bot startup and update logs. | Admin only |
| `/clear_staff_role` | Clear the staff role so only Administrators can use staff commands. | Admin only |

---

## Roster Monitor

| Command | Description | Permission |
|---------|-------------|------------|
| `/set_roster_channel channel:` | Set the destination channel for roster audit reports. | Staff or Admin |
| `/roster_audit` | Manually trigger an audit of all verified members' RSI org membership status. Results posted to the audit channel. | Staff or Admin |
| `/org_full_sync [org:]` | Compare one or all RSI org rosters against the verification database. Lists RSI members not yet linked. | Staff or Admin |

> Roster audits also run automatically on a **weekly background loop**.

---

## Reaction Roles

| Command | Description | Permission |
|---------|-------------|------------|
| `/setup_reaction_role role: emoji: message:` | Post an embed with a reaction that grants/removes `role` when clicked. | Admin only (Manage Roles) |

---

## Automated Notifications

- **Reboot & Update Alerts** — On startup, the bot sends a message to the channel specified by `LOG_CHANNEL_ID` in `.env`, showing the current git branch and latest commit message.
