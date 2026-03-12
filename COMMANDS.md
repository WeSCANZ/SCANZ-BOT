# SCANZ-BOT Command Guide

This document lists all available commands for the SCANZ-BOT, organized by who has permission to use them.

## Permission Levels

- **All Users (Everyone)** – Any member can use the command.
- **Admin / Officer (Staff)** – User must have the **Staff role** (configured via `/set_staff_role`) **or** *Administrator*. Used for managing the bot's core features.
- **Administrator** – User must have the *Administrator* permission. Used to configure the staff role itself.
- **Manage Roles** – User must have the *Manage Roles* permission (or Administrator).

---

## 1. All Users (Everyone) 

These commands are available for any server member to use.

### Utility & Fun
- `**/hi**`: Says hello with a random, personalized message.
- `**/time**`: Displays the current time across major SCANZ timezones.
- `**/ping**`: Checks the bot's global latency and connection speed.
- `**@SCANZ_BOT [message]**`: the bot will intelligently reply to keyword mentions or provide witty responses.
- `**/scanz_commands**`: Lists all available commands for the bot directly in an ephemeral Discord embed.



### Verification & Organization
- `**/verify**`: Link your Discord account to your RSI Handle using a unique bio checksum. optionally specify `org: [ORG]`.
- `**/list_orgs**`: Displays the currently configured organisation symbols for verification.

### Feedback & Pings
- `**/ping**`: Creates a formatted alert/ping (Event/Announcement) and automatically pings the `@SCANZ` role. Usage: `/ping game_loop:"Org Event" description:"QV RUN IN NYX"`
- `**/suggestion**`: Submit feedback or an idea to the staff. Set `anonymous:True` to hide your username.

---

## 2. Admin & Officer Commands (Staff)

These commands require the user to have the designated Staff role or server wide Administrator permissions.

### Message Enforcement & Channels
- `**/enforce_channel**`: Toggle strict message enforcement (Event/Ping format only) for the current channel.
- `**/scanz_format**`: Interactively set the allowed "Post Types" and "Game Loops" for an enforced channel.
- `**/set_ping_target**`: Set the default target channel for ping posts.
- `**/scanz_subscriptions**`: Post a persistent message to a channel with buttons for members to subscribe/unsubscribe from ping roles.
- `**/set_suggestion_channel**`: Set the destination channel for suggestions submitted via `/suggestion`.

### Verification Management
- `**/add_org**`: Add an RSI organisation or affiliate symbol to the configuration.
- `**/remove_org**`: Remove an organisation symbol from the configuration.
- `**/set_main_role**`: Set the role granted to verified Main Org members.
- `**/set_affiliate_role**`: Set the role granted to verified Affiliate members.
- `**/set_guest_role**`: Set the role granted to verified Honored Guests (non-org).
- `**/set_unverified_role**`: Set the role applied to users needing verification (unlinked RSI).
- `**/set_scanz_role**`: Configure an optional filter role for checking who should be verified.
- `**/grant_verified**`: Manually apply the correct roles/nicknames based on a user's verification state.
- `**/manual_verify**`: Manually initiate the verification process for a member and an RSI handle (generates a checksum challenge).
- `**/search_verified**`: Search for a verified member by handle, Discord ID, or mention.
- `**/export_verified**`: Export the entire verification database as a CSV file.

### Roster Monitoring
- `**/set_roster_channel**`: Set the destination channel for weekly roster audit reports.
- `**/roster_audit**`: Manually trigger a check of all verified members to ensure they are still active in their configured RSI organisation.
- `**/org_full_sync**`: Perform a comprehensive sync between an RSI organisation roster and the bot's verification database to find discrepancies.

---

## 3. Administrator / Specialized Commands

These commands require strict server permissions (Administrator or Manage Roles).

- `**/set_staff_role**`: *(Administrator Only)* Set the role that can use all Staff commands (e.g. Officer / Custodian). 
- `**/clear_staff_role**`: *(Administrator Only)* Clear the staff role so that only users with Administrator can use Staff commands.
- `**/setup_reaction_role**`: *(Manage Roles)* Creates a message with a specific reaction that assigns a role when clicked. Usage: `/setup_reaction_role role:@Role emoji:👍 message:"Click!"`.

---

## Automated Notifications
- **Reboot & Update Alerts**: The bot automatically sends a notification to the designated log channel whenever it reboots or is updated, showing the current git branch and latest commit message. (Requires `LOG_CHANNEL_ID` in `.env`).
