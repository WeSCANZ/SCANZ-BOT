# SCANZ-BOT Command Guide

This document lists all available commands for the SCANZ-BOT.

## General Commands
*   **`!hi`**
    *   **Description**: Says hello with a random strange/verbose message.
    *   **Usage**: `!hi`
    *   **Permission**: Everyone
*   **`!time`**
    *   **Description**: Displays the current time across major SCANZ timezones (Indochina, Perth, Melbourne/Sydney, New Zealand).
    *   **Usage**: `!time`
    *   **Permission**: Everyone
*   **`@SCANZ_BOT [message]`**
    *   **Description**: The bot will intelligently reply to keyword mentions (e.g. "website", "discord", "help") and fallback to random witty responses.
    *   **Usage**: Tag `@SCANZ_BOT` anywhere in a channel.
    *   **Permission**: Everyone
*   **`/scanz_commands`** (Slash Command)
    *   **Description**: Lists all available commands for the bot directly in an ephemeral Discord embed.
    *   **Usage**: `/scanz_commands`
    *   **Permission**: Everyone

## Reaction Roles
*   **`/setup_reaction_role`** (Slash Command)
    *   **Description**: Creates a message with a specific reaction that assigns a role when clicked.
    *   **Usage**: `/setup_reaction_role role:@Role emoji:👍 message:"Click to get role!"`
    *   **Arguments**:
        *   `role`: The role to give/remove.
        *   `emoji`: The emoji to react with.
        *   `message`: The text content of the embed.
    *   **Permission**: Admin / Manage Roles (Implicit in Discord permissions)

## Message Enforcement (Slash Commands)
*   **`/enforce_channel`**
    *   **Description**: Admin command to toggle strict message enforcement (Event/Ping/Announcement format only) for the current channel.
    *   **Usage**: `/enforce_channel enabled:True`
    *   **Arguments**:
        *   `enabled`: True to enable, False to disable.
    *   **Permission**: Admin
*   **`/scanz_format`**
    *   **Description**: Admin command to interactively set the allowed "Post Types" and "Game Loops" for an enforced channel. Posts an informational embed when saved.
    *   **Usage**: `/scanz_format`
    *   **Permission**: Admin
*   **`/set_post_target`**
    *   **Description**: Admin command to set a default designated target channel for a specific post type (e.g., all `EVENT` posts automatically route to `#org-events`).
    *   **Usage**: `/set_post_target type:EVENT channel:#org-events`
    *   **Permission**: Admin
*   **`/scanz_subscriptions`**
    *   **Description**: Admin command to post a persistent message with buttons for members to subscribe/unsubscribe from ping roles.
    *   **Usage**: `/scanz_subscriptions`
    *   **Permission**: Admin
*   **`/ping`**
    *   **Description**: Creates a formatted alert/ping. This command automatically pings the `@SCANZ` role.
    *   **Usage**: `/ping game_loop:"Org Event" description:"QV RUN IN NYX" time:"1:00pm Melbourne" location:"Nyx" requirements:"Armour, Weapons, Meds" channel:#org-events`
    *   **Arguments**:
        *   `game_loop`: Select the type of activity (e.g., Mining, Bounties, Org Event).
        *   `description`: What are we doing?
        *   `time` *(Optional)*: When is it happening?
        *   `location` *(Optional)*: Where is it starting?
        *   `requirements` *(Optional)*: What should people bring?
        *   `link` *(Optional)*: Link to a voice channel or event page.
        *   `channel` *(Optional)*: Specifically pick an enforced channel to cross-post to. If left blank, falls back to the database-configured default for "Ping" or the current channel.
    *   **Permission**: Everyone

## Verification Commands
*   **`/verify`** (Slash Command)
    *   **Description**: Link your Discord account to your RSI Handle using a unique bio checksum.
    *   **Usage**: `/verify handle:[Your_RSI_Handle]`
    *   **Arguments**:
        *   `handle`: Your exact Star Citizen RSI Handle.
    *   **Permission**: Everyone
*   **`/set_verified_role`** (Slash Command)
    *   **Description**: Admin command to set the role granted upon successful RSI Verification.
    *   **Usage**: `/set_verified_role role:@Verified`
    *   **Arguments**:
        *   `role`: The role to grant verified users.
    *   **Permission**: Admin
*   **`/grant_verified`** (Slash Command)
    *   **Description**: Admin shortcut to manually apply the verified role and RSI Handle nickname to an already-verified member.
    *   **Usage**: `/grant_verified member:@SomeUser`
    *   **Arguments**:
        *   `member`: The Discord member to apply the verified role and nickname to.
    *   **Permission**: Admin

## Roster Monitor (Admin)
*   **`/roster_audit`** (Slash Command)
    *   **Description**: Manually triggers a check of all verified members to ensure they are still in the SCANZ organization on RSI.
    *   **Permission**: Admin
*   **`/set_roster_channel`** (Slash Command)
    *   **Description**: Sets the destination for weekly roster audit reports.
    *   **Permission**: Admin

## Suggestion Box
*   **`/suggestion`** (Slash Command)
    *   **Description**: Submit feedback or an idea to the staff.
    *   **Usage**: `/suggestion text:"Your idea" anonymous:True`
    *   **Arguments**:
        *   `text`: The content of your suggestion.
        *   `anonymous`: (Optional) Set to True to hide your name from staff.
    *   **Permission**: Everyone
*   **`/set_suggestion_channel`** (Slash Command)
    *   **Description**: Admin command to set the destination channel for suggestions.
    *   **Usage**: `/set_suggestion_channel channel:#suggestions-logs`
    *   **Permission**: Admin

## Utility
*   **`!ping`**
    *   **Description**: Checks if the bot is responsive.
    *   **Usage**: `!ping`
    *   **Response**: `Pong!`

## Star Citizen Utilities
*   **`!status`**
    *   **Description**: Fetches current server status from status.robertsspaceindustries.com.
    *   **Usage**: `!status`
*   **`!wiki [term]`**
    *   **Description**: Generates a search link for the Star Citizen Wiki.
    *   **Usage**: `!wiki Cutlass Black`
*   **`!org`**
    *   **Description**: Displays information and links for SCANZ.
    *   **Usage**: `!org`
