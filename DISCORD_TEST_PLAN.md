# SCANZ-BOT Discord Test Plan

Manual test checklist. Run in order — later tests depend on earlier configuration steps being complete.

> **Legend:** `[A]` = Admin account required · `[S]` = Staff account required · `[U]` = Regular user account

---

## Phase 1 — Bot Health & Startup

| # | Action | Expected Result |
|---|--------|----------------|
| 1.1 | Start / redeploy the bot | Bot posts a startup message in the `LOG_CHANNEL_ID` channel containing the branch name and latest commit message |
| 1.2 | `/latency` | Ephemeral embed appears showing `🏓 Pong! WebSocket Latency: XXms` |
| 1.3 | `/hi` | Bot replies with a random personalised greeting |
| 1.4 | `/time` | Embed appears with 4 timezone fields (ICT, AWST, AET, NZT) showing current local times |
| 1.5 | `/scanz_commands` | Ephemeral embed appears listing all commands, grouped by section |
| 1.6 | Mention `@SCANZ_BOT` with the word `website` | Bot replies with the wescanz.com link |
| 1.7 | Mention `@SCANZ_BOT` with a random message | Bot replies with a random witty fallback response |

---

## Phase 2 — Admin Role & Staff Configuration

> Run these before any staff-gated commands.

| # | Action | Expected Result |
|---|--------|----------------|
| 2.1 `[A]` | `/set_staff_role role:@YourStaffRole` | Confirmation: *"✅ Staff role set to @YourStaffRole"* |
| 2.2 `[U]` | Attempt `/set_main_role role:@SomeRole` (as a non-staff, non-admin user) | Bot replies: *"You don't have permission to use this command."* |
| 2.3 `[S]` | Attempt `/set_main_role role:@SomeRole` (as a staff member) | Succeeds — confirms staff role check is working |
| 2.4 `[A]` | `/clear_staff_role` | Confirmation: *"✅ Staff role cleared. Only Administrator can use staff commands."* |
| 2.5 `[A]` | `/set_staff_role role:@YourStaffRole` | Re-set staff role for remaining tests |

---

## Phase 3 — RSI Verification Setup

| # | Action | Expected Result |
|---|--------|----------------|
| 3.1 `[S]` | `/add_org symbol:SCANZ` | *"✅ Added organisation `SCANZ`"* |
| 3.2 `[S]` | `/add_org symbol:SCANZ` (again) | *"ℹ️ `SCANZ` is already configured."* |
| 3.3 | `/list_orgs` | Returns *"Configured organisations: SCANZ"* |
| 3.4 `[S]` | `/set_main_role role:@MainMember` | Confirmation |
| 3.5 `[S]` | `/set_affiliate_role role:@Affiliate` | Confirmation |
| 3.6 `[S]` | `/set_guest_role role:@HonoredGuest` | Confirmation |
| 3.7 `[S]` | `/set_unverified_role role:@NeedsVerification` | Confirmation |
| 3.8 `[S]` | `/set_scanz_role role:@SCANZ` | Confirmation |

---

## Phase 4 — Verification Flow (Member)

| # | Action | Expected Result |
|---|--------|----------------|
| 4.1 `[U]` | `/verify handle:YourRSIHandle org:SCANZ` | Ephemeral embed with unique challenge code and "Verify Now" button |
| 4.2 `[U]` | Add the challenge code to your RSI Short Bio, then click **Verify Now** | *"✅ Verification Successful!"* — correct role (`Main`, `Affiliate`, or `Guest`) is applied |
| 4.3 `[U]` | `/verify handle:YourRSIHandle org:SCANZ` (again) | *"You are already verified for SCANZ..."* |
| 4.4 `[U]` | Manually change your Discord nickname to something that doesn't include your RSI handle | Bot auto-corrects nickname back to the RSI handle |

---

## Phase 5 — Staff Verification Tools

| # | Action | Expected Result |
|---|--------|----------------|
| 5.1 `[S]` | `/search_verified query:YourRSIHandle` | Embed showing matching Discord member and org |
| 5.2 `[S]` | `/search_verified query:99999999` (nonexistent ID) | *"No results found"* |
| 5.3 `[S]` | `/export_verified` | Bot sends a CSV file attachment with verified member data |
| 5.4 `[S]` | `/export_unverified` | Bot sends a CSV file of non-verified members |
| 5.5 `[S]` | `/export_unverified role:@SCANZ` | CSV filtered to only members with that role |
| 5.6 `[S]` | `/grant_verified member:@SomeVerifiedUser` | Confirmation that correct role was applied |
| 5.7 `[S]` | `/grant_verified member:@UnverifiedUser` | Error: *"Not verified in database. They must complete `/verify` first."* |
| 5.8 `[S]` | `/manual_verify member:@TestUser handle:TestHandle org:SCANZ` | Challenge embed with "Complete Verification" button; after RSI bio is updated, click button to complete |
| 5.9 `[S]` | `/remove_org symbol:TESTORG` (nonexistent) | *"⚠️ `TESTORG` was not configured."* |

---

## Phase 6 — Message Enforcer

| # | Action | Expected Result |
|---|--------|----------------|
| 6.1 `[S]` | In a **test channel**, run `/enforce_channel enabled:True` | *"Message enforcement has been enabled for this channel."* |
| 6.2 `[U]` | Type a regular message in the enforced channel | Message is deleted; user receives a DM warning |
| 6.3 `[S]` | `/scanz_format` (in the enforced channel) | Interactive dropdown to choose Game Loops + Save button |
| 6.4 `[S]` | Select a game loop and click **Save Configuration & Post Info** | Config saved; informational embed posted in the channel |
| 6.5 `[S]` | `/set_ping_target channel:#your-events-channel` | Confirmation |
| 6.6 `[U]` | `/ping game_loop:General description:"Test ping"` | Embed with `@SCANZ` mention posted in the configured target channel; ephemeral confirmation to user |
| 6.7 `[U]` | `/ping game_loop:General description:"Test ping" channel:#different-channel` | Embed posted in the explicitly specified channel |
| 6.8 `[S]` | `/enforce_channel enabled:False` | Enforcement disabled; regular messages no longer deleted |

---

## Phase 7 — Ping Role Subscriptions

| # | Action | Expected Result |
|---|--------|----------------|
| 7.1 `[S]` | `/scanz_subscriptions` | Embed with subscription toggle buttons posted in the current channel |
| 7.2 `[U]` | Click a subscription button | *"✅ Subscribed to **RoleName**."* — role is added |
| 7.3 `[U]` | Click the same button again | *"✅ Unsubscribed from **RoleName**."* — role is removed |
| 7.4 | Restart the bot | Subscription buttons still work (persistent view) |

---

## Phase 8 — Reaction Roles

| # | Action | Expected Result |
|---|--------|----------------|
| 8.1 `[A]` | `/setup_reaction_role role:@TestRole emoji:✅ message:"Click ✅ to get the Test role!"` | Embed posted with a ✅ reaction added by the bot |
| 8.2 `[U]` | Click the ✅ reaction | `@TestRole` is applied to the user |
| 8.3 `[U]` | Remove the ✅ reaction | `@TestRole` is removed from the user |
| 8.4 | Restart the bot | Reaction role still works (loaded from DB on startup) |

---

## Phase 9 — Suggestions

| # | Action | Expected Result |
|---|--------|----------------|
| 9.1 `[S]` | `/set_suggestion_channel channel:#suggestions` | Confirmation |
| 9.2 `[U]` | `/suggestion text:"Test suggestion" anonymous:False` | Embed posted in `#suggestions` with author name; discussion thread created; user gets ephemeral confirmation |
| 9.3 `[U]` | `/suggestion text:"Anonymous idea" anonymous:True` | Embed posted with *"Anonymous Member"* as author |
| 9.4 `[S]` | Reply in the discussion thread created in 9.2 | Original suggester receives a DM notification linking to the reply |
| 9.5 `[U]` | `/suggestion text:"No channel test"` (before 9.1 is run on a fresh server) | Error: *"Suggestions are not currently enabled..."* |

---

## Phase 10 — Roster Monitor

| # | Action | Expected Result |
|---|--------|----------------|
| 10.1 `[S]` | `/set_roster_channel channel:#roster-audit` | Confirmation |
| 10.2 `[S]` | `/roster_audit` | Deferred response; audit runs; results embed posted in `#roster-audit` (clean = green, anomalies = red) |
| 10.3 `[S]` | `/org_full_sync` (all orgs) | Fetches RSI roster; embed showing unlinked RSI members vs database |
| 10.4 `[S]` | `/org_full_sync org:SCANZ` | Same but scoped to SCANZ only |
| 10.5 `[S]` | `/org_full_sync org:INVALID` | Error: *"❌ Unknown org `INVALID`."* |

---

## Phase 11 — Edge Cases & Error Handling

| # | Action | Expected Result |
|---|--------|----------------|
| 11.1 `[U]` | `/verify handle:NonExistentHandle123xyz org:SCANZ` and click Verify | *"Could not find an RSI Citizen record for the handle..."* |
| 11.2 `[U]` | `/verify handle:ValidHandle org:SCANZ`, add wrong code to bio, click Verify | *"The code was not found in your Short Bio..."* |
| 11.3 `[S]` | `/roster_audit` when `RSIVerification` cog is not loaded | *"❌ RSIVerification cog is not loaded."* |
| 11.4 | Restart bot with no `LOG_CHANNEL_ID` set | Warning printed to console; bot starts normally |
 
 ---
 
 ## Phase 12 — Admin Action Logging
 
 | # | Action | Expected Result |
 |---|--------|----------------|
 | 12.1 `[A]` | Start the bot with `ADMIN_LOG_CHANNEL_ID` configured | Bot posts a startup message in the admin log channel |
 | 12.2 `[S]` | `/enforce_channel mode:Strict` | Embed in `ADMIN_LOG_CHANNEL_ID` showing the config change |
 | 12.3 `[U]` | Type a regular message in a strictly enforced channel | "Strict Enforcement: Message Deleted" embed posted to admin log |
 | 12.4 `[S]` | `/enforcer_user_reminder user:@TestUser message:"Hello" punishment_type:Timeout punishment_value:60` | "User Reminder Updated" embed posted to admin log |
 | 12.5 `[U]` | Targeted user posts a message | "User Punishment Applied" embed posted to admin log (with Timeout details) |
 | 12.6 `[S]` | `/set_suggestion_channel channel:#suggestions` | "Log Configuration Updated" (Suggestion Channel) embed in admin log |
 | 12.7 `[S]` | `/setup_reaction_role ...` | "Reaction Role Created" embed in admin log |
 | 12.8 `[S]` | `/roster_audit` or `/org_full_sync` | Embed in `ADMIN_LOG_CHANNEL_ID` noting the manual trigger |
 | 12.9 `[S]` | Verify successful verification flow | "User Verified Successfully" embed in admin log |
