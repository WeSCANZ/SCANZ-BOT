# SCANZ-BOT Command Guide

This document lists all available commands for the SCANZ-BOT.

## Permission Levels

- **Everyone** – Any member can use the command.
- **Manage Roles** – User must have the *Manage Roles* permission (or Administrator).
- **Staff** – User must have the **Staff role** (configured via `/set_staff_role`) **or** *Administrator*. If no staff role is set, only *Administrator* can use these commands.
- **Administrator** – User must have the *Administrator* permission. Used only for commands that configure who gets Staff access.

## General Commands

- `**!hi**`
  - **Description**: Says hello with a random strange/verbose message.
  - **Usage**: `!hi`
  - **Permission**: Everyone
- `**!time`**
  - **Description**: Displays the current time across major SCANZ timezones (Indochina, Perth, Melbourne/Sydney, New Zealand).
  - **Usage**: `!time`
  - **Permission**: Everyone
- `**@SCANZ_BOT [message]`**
  - **Description**: The bot will intelligently reply to keyword mentions (e.g. "website", "discord", "help") and fallback to random witty responses.
  - **Usage**: Tag `@SCANZ_BOT` anywhere in a channel.
  - **Permission**: Everyone
- `**/scanz_commands`** (Slash Command)
  - **Description**: Lists all available commands for the bot directly in an ephemeral Discord embed.
  - **Usage**: `/scanz_commands`
  - **Permission**: Everyone

## Reaction Roles

- `**/setup_reaction_role`** (Slash Command)
  - **Description**: Creates a message with a specific reaction that assigns a role when clicked.
  - **Usage**: `/setup_reaction_role role:@Role emoji:👍 message:"Click to get role!"`
  - **Arguments**:
    - `role`: The role to give/remove.
    - `emoji`: The emoji to react with.
    - `message`: The text content of the embed.
  - **Permission**: Manage Roles

## Message Enforcement (Slash Commands)

- `**/enforce_channel`**
  - **Description**: Toggle strict message enforcement (Event/Ping/Announcement format only) for the current channel.
  - **Usage**: `/enforce_channel enabled:True`
  - **Arguments**:
    - `enabled`: True to enable, False to disable.
  - **Permission**: Staff
- `**/scanz_format`**
  - **Description**: Interactively set the allowed "Post Types" and "Game Loops" for an enforced channel. Posts an informational embed when saved.
  - **Usage**: `/scanz_format`
  - **Permission**: Staff
- `**/set_ping_target`**
  - **Description**: Set the default target channel for ping posts (e.g. all pings from this context route to `#org-events`).
  - **Usage**: `/set_ping_target channel:#org-events`
  - **Permission**: Staff
- `**/scanz_subscriptions`**
  - **Description**: Post a persistent message with buttons for members to subscribe/unsubscribe from ping roles.
  - **Usage**: `/scanz_subscriptions`
  - **Permission**: Staff
- `**/ping`**
  - **Description**: Creates a formatted alert/ping. This command automatically pings the `@SCANZ` role.
  - **Usage**: `/ping game_loop:"Org Event" description:"QV RUN IN NYX" time:"1:00pm Melbourne" location:"Nyx" requirements:"Armour, Weapons, Meds" channel:#org-events`
  - **Arguments**:
    - `game_loop`: Select the type of activity (e.g., Mining, Bounties, Org Event).
    - `description`: What are we doing?
    - `time` *(Optional)*: When is it happening?
    - `location` *(Optional)*: Where is it starting?
    - `requirements` *(Optional)*: What should people bring?
    - `link` *(Optional)*: Link to a voice channel or event page.
    - `channel` *(Optional)*: Specifically pick an enforced channel to cross-post to. If left blank, falls back to the database-configured default for "Ping" or the current channel.
  - **Permission**: Everyone

## Verification Commands

- `**/verify`** (Slash Command)
  - **Description**: Link your Discord account to your RSI Handle using a unique bio checksum. Optionally specify which organisation/affiliate you are verifying for.
  - **Usage**: `/verify handle:[Your_RSI_Handle] org:[ORG]`
  - **Arguments**:
    - `handle`: Your exact Star Citizen RSI Handle.
    - `org` *(Optional)*: Symbol of the organisation/affiliate (autocomplete supported).
  - **Permission**: Everyone
- `**/set_staff_role`** (Slash Command)
  - **Description**: *Administrator only.* Set the role that can use all Staff commands (e.g. Custodian). Users with this role or Administrator can use enforce, verification, suggestions, and roster commands.
  - **Usage**: `/set_staff_role role:@Custodian`
  - **Permission**: Administrator
- `**/clear_staff_role`** (Slash Command)
  - **Description**: *Administrator only.* Clear the staff role so that only users with Administrator can use Staff commands.
  - **Usage**: `/clear_staff_role`
  - **Permission**: Administrator
- `**/set_verified_role`** (Slash Command)
  - **Description**: Set the role granted upon successful RSI Verification.
  - **Usage**: `/set_verified_role role:@Verified`
  - **Arguments**:
    - `role`: The role to grant verified users.
  - **Permission**: Staff
- `**/set_scanz_role`**
  - **Description**: Configure the role that identifies SCANZ members (used for enforcement and audit tagging).
  - **Usage**: `/set_scanz_role role:@SCANZ`
  - **Permission**: Staff
- `**/set_needs_role`**
  - **Description**: Set the role that will be applied to members needing verification.
  - **Usage**: `/set_needs_role role:@NeedsVerification`
  - **Permission**: Staff
- `**/add_org`**
  - **Description**: Add an RSI organisation or affiliate symbol to the configuration.
  - **Usage**: `/add_org symbol:SCANZ`
  - **Permission**: Staff
- `**/remove_org`**
  - **Description**: Remove an organisation symbol from the configuration.
  - **Usage**: `/remove_org symbol:SCANZ`
  - **Permission**: Staff
- `**/list_orgs`**
  - **Description**: Displays the currently configured organisation symbols.
  - **Usage**: `/list_orgs`
  - **Permission**: Everyone
- `**/grant_verified`** (Slash Command)
  - **Description**: Manually apply the verified role and RSI Handle nickname to an already-verified member.
  - **Usage**: `/grant_verified member:@SomeUser`
  - **Arguments**:
    - `member`: The Discord member to apply the verified role and nickname to.
  - **Permission**: Staff
- `**/manual_verify`** (Slash Command)
  - **Description**: Manually initiate the verification process for a member and an RSI handle. Generates a checksum challenge. You may indicate which organisation this verification is for.
  - **Usage**: `/manual_verify member:@SomeUser handle:RSI_Handle org:[ORG]`
  - **Arguments**:
    - `member`: The Discord member to verify.
    - `handle`: The RSI handle to link.
    - `org` *(Optional)*: Organisation symbol (autocomplete).
  - **Permission**: Staff
- `**/export_verified`** (Slash Command)
  - **Description**: Export the entire verification database as a CSV file.
  - **Usage**: `/export_verified`
  - **Permission**: Staff
- `**/search_verified`** (Slash Command)
  - **Description**: Search for a verified member by handle, Discord ID, or mention.
  - **Usage**: `/search_verified query:Petri`
  - **Arguments**:
    - `query`: The RSI handle, Discord ID, or mention to search for.
  - **Permission**: Staff

## Roster Monitor

- `**/set_roster_channel`** (Slash Command)
  - **Description**: Set the destination channel for weekly roster audit reports.
  - **Usage**: `/set_roster_channel channel:#roster-audit`
  - **Permission**: Staff
- `**/roster_audit`** (Slash Command)
  - **Description**: Manually trigger a check of all verified members (optionally limited by org) to ensure they are still active in their configured RSI organisation.
  - **Usage**: `/roster_audit`
  - **Permission**: Staff
- `**/org_full_sync`** (Slash Command)
  - **Description**: Perform a comprehensive sync between one or all RSI organisation rosters and the bot's verification database. Identifies unlinked RSI members.
  - **Usage**: `/org_full_sync org:[ORG]` (org parameter is optional)
  - **Permission**: Staff

## Suggestion Box

- `**/suggestion`** (Slash Command)
  - **Description**: Submit feedback or an idea to the staff.
  - **Usage**: `/suggestion text:"Your idea" anonymous:True`
  - **Arguments**:
    - `text`: The content of your suggestion.
    - `anonymous`: (Optional) Set to True to hide your name from staff.
  - **Permission**: Everyone
- `**/set_suggestion_channel`** (Slash Command)
  - **Description**: Set the destination channel for suggestions.
  - **Usage**: `/set_suggestion_channel channel:#suggestions-logs`
  - **Permission**: Staff

## Utility

- `**!ping`**
  - **Description**: Checks if the bot is responsive.
  - **Usage**: `!ping`
  - **Response**: `Pong!`
  - **Permission**: Everyone

## Star Citizen Utilities

- `**!status`**
  - **Description**: Fetches current server status from status.robertsspaceindustries.com.
  - **Usage**: `!status`
  - **Permission**: Everyone
- `**!wiki [term]`**
  - **Description**: Generates a search link for the Star Citizen Wiki.
  - **Usage**: `!wiki Cutlass Black`
  - **Permission**: Everyone
- `**!org`**
  - **Description**: Displays information and links for SCANZ.
  - **Usage**: `!org`
  - **Permission**: Everyone

## Automated Notifications

- **Reboot & Update Alerts**
  - **Description**: The bot automatically sends a notification to the designated log channel whenever it reboots or is updated. This message includes the current git branch and the latest commit message for version tracking.
  - **Configuration**: Requires `LOG_CHANNEL_ID` in the `.env` file.

