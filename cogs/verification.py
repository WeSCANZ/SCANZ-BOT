import csv
import io
import os
import random
import sqlite3
import string

import aiohttp
import discord
from bs4 import BeautifulSoup
from discord import app_commands
from discord.ext import commands

from utils.checks import has_staff_or_admin


class VerifyNowView(discord.ui.View):
    def __init__(self, cog, handle: str, code: str, org: str | None = None):
        super().__init__(timeout=None)
        self.cog = cog
        self.handle = handle
        self.code = code
        self.org = org

    @discord.ui.button(label="Verify Now", style=discord.ButtonStyle.success, emoji="✅")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        success, message = await self.cog._scrape_rsi_bio(self.handle, self.code)

        if success:
            # 1. Update database
            target_org = self.org
            # if scraping returned an org and user didn't specify one, use it
            if not target_org and isinstance(message, dict):
                target_org = message.get("org")

            # Determine Org Status dynamically via RSI (Main / Affiliate / None)
            org_status, org_rank = await self.cog._check_org_status(self.handle, target_org)

            self.cog._link_account(
                interaction.user.id,
                self.handle,
                target_org,
                org_status,
                org_rank,
            )

            # Fetch the actual Member object from the guild (interaction.user is a User, not a Member)
            member = None
            if interaction.guild:
                member = interaction.guild.get_member(interaction.user.id)
                if member is None:
                    try:
                        member = await interaction.guild.fetch_member(interaction.user.id)
                    except discord.NotFound:
                        member = None

            if member:
                # 2. Update discord nickname (DISABLED - Permission Issues)
                # try:
                #     await member.edit(nick=self.handle)
                # except discord.Forbidden:
                #     print(f"[Verify] Forbidden: Could not set nickname for {member}")

                # 3. Add Verified Role (sync will also remove needs-role if present)
                await self.cog.sync_member_roles(member)

                # Log admin action
                embed = discord.Embed(
                    title="User Verified Successfully",
                    description=(
                        f"**User:** {member.mention} ({member.id})\n"
                        f"**RSI Handle:** `{self.handle}`\n"
                        f"**Org:** `{target_org}`\n"
                        f"**Status:** `{org_status}`\n"
                        f"**Rank:** `{org_rank}`"
                    ),
                    color=discord.Color.green(),
                    timestamp=discord.utils.utcnow(),
                )
                await self.cog.bot.log_admin_action(embed)

            await interaction.followup.send(
                f"✅ **Verification Successful!** Your Discord account is now officially linked to the "
                f"RSI Handle **{self.handle}**.\n\nYou may now remove the code from your RSI Short Bio.",
                ephemeral=True,
            )
            self.stop()
        else:
            await interaction.followup.send(
                f"❌ **Verification Failed:** {message}\n\nPlease ensure you have correctly pasted "
                f"` {self.code} ` into your Short Bio and try again.",
                ephemeral=True,
            )


async def org_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete helper for organisation parameters."""
    client = interaction.client
    orgs = []
    if isinstance(client, commands.Bot):
        cog = client.get_cog("RSIVerification")
        if cog and hasattr(cog, "_get_orgs"):
            orgs = getattr(cog, "_get_orgs")()
    return [app_commands.Choice(name=o, value=o) for o in orgs if current.lower() in o.lower()]


class RSIVerification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "data/enforcer.db"
        # in-memory cache of configured org symbols; loaded on demand
        self._org_cache: list[str] | None = None
        self._setup_db()

    def _setup_db(self):
        """Create or migrate the database schema.

        The `rsi_links` table is rebuilt if necessary so that it contains the
        composite primary key `(discord_id, org_handle)` and uses the
        `org_handle` column name consistently.
        """
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # ensure config table exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rsi_config (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            # examine existing links schema
            cursor.execute("PRAGMA table_info(rsi_links)")
            cols = cursor.fetchall()
            col_names = [c[1] for c in cols]
            has_org_handle = "org_handle" in col_names
            has_org = "org" in col_names

            # if table missing or requires migration, rebuild it
            if not cols or (has_org and not has_org_handle) or (cols and not has_org_handle):
                # create a new table with desired schema
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS rsi_links_new (
                        discord_id INTEGER,
                        rsi_handle TEXT NOT NULL,
                        org_handle TEXT NOT NULL DEFAULT 'SCANZ',
                        PRIMARY KEY(discord_id, org_handle)
                    )
                """)
                # copy existing data if any
                if cols:
                    # handle both old column names
                    if has_org_handle:
                        cursor.execute(
                            "INSERT OR IGNORE INTO rsi_links_new(discord_id, rsi_handle, org_handle)"
                            " SELECT discord_id, rsi_handle, org_handle FROM rsi_links"
                        )
                    elif has_org:
                        cursor.execute(
                            "INSERT OR IGNORE INTO rsi_links_new(discord_id, rsi_handle, org_handle)"
                            " SELECT discord_id, rsi_handle, COALESCE(org, 'SCANZ') FROM rsi_links"
                        )
                    else:
                        cursor.execute(
                            "INSERT OR IGNORE INTO rsi_links_new(discord_id, rsi_handle, org_handle)"
                            " SELECT discord_id, rsi_handle, 'SCANZ' FROM rsi_links"
                        )
                # drop old table and rename
                cursor.execute("DROP TABLE IF EXISTS rsi_links")
                cursor.execute("ALTER TABLE rsi_links_new RENAME TO rsi_links")

            # Add org_status and org_rank columns if they don't exist
            cursor.execute("PRAGMA table_info(rsi_links)")
            cols = cursor.fetchall()
            col_names = [c[1] for c in cols]
            if "org_status" not in col_names:
                cursor.execute("ALTER TABLE rsi_links ADD COLUMN org_status TEXT DEFAULT 'None'")
            if "org_rank" not in col_names:
                cursor.execute("ALTER TABLE rsi_links ADD COLUMN org_rank TEXT DEFAULT 'None'")
            conn.commit()

    def _set_config(self, key: str, value: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO rsi_config (key, value)
                VALUES (?, ?)
            """,
                (key, value),
            )
            conn.commit()

    def _get_config(self, key: str) -> str | None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM rsi_config WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else None

    # -------------------------------------------------------------
    # organisation helpers
    # -------------------------------------------------------------
    def _get_orgs(self) -> list[str]:
        """Return the list of configured RSI organisation/affiliate symbols."""
        if self._org_cache is not None:
            return self._org_cache
        val = self._get_config("org_handles")
        if not val:
            self._org_cache = []
        else:
            self._org_cache = [s.strip().upper() for s in val.split(",") if s.strip()]
        return self._org_cache

    def _add_org(self, org: str) -> bool:
        """Add a symbol to the org list. Returns True if added."""
        org = org.upper()
        orgs = self._get_orgs()
        if org in orgs:
            return False
        orgs.append(org)
        self._set_config("org_handles", ",".join(orgs))
        self._org_cache = orgs
        return True

    def _remove_org(self, org: str) -> bool:
        """Remove a symbol from the org list. Returns True if removed."""
        org = org.upper()
        orgs = self._get_orgs()
        if org not in orgs:
            return False
        orgs = [o for o in orgs if o != org]
        self._set_config("org_handles", ",".join(orgs))
        self._org_cache = orgs
        return True

    def _is_verified(self, discord_id: int, org: str | None = None) -> str | None:
        """Return the linked RSI handle for the given discord ID.

        If `org` is provided we restrict to that organisation, otherwise
        we return the first matching handle regardless of org.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if org:
                cursor.execute(
                    "SELECT rsi_handle FROM rsi_links WHERE discord_id = ? AND org_handle = ?",
                    (discord_id, org.upper()),
                )
            else:
                cursor.execute(
                    "SELECT rsi_handle FROM rsi_links WHERE discord_id = ?",
                    (discord_id,),
                )
            row = cursor.fetchone()
            return row[0] if row else None

    def _link_account(
        self,
        discord_id: int,
        handle: str,
        org: str | None = None,
        org_status: str = "None",
        org_rank: str = "None",
    ):
        # pick a default org if none supplied
        if not org:
            orgs = self._get_orgs()
            org = orgs[0] if orgs else ""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO rsi_links (discord_id, rsi_handle, org_handle, org_status, org_rank)
                VALUES (?, ?, ?, ?, ?)
            """,
                (discord_id, handle, org, org_status, org_rank),
            )
            conn.commit()

    async def _scrape_rsi_bio(self, handle: str, code: str) -> tuple[bool, str | dict]:
        url = f"https://robertsspaceindustries.com/citizens/{handle}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status == 404:
                        return False, f"Could not find an RSI Citizen record for the handle '{handle}'."
                    elif response.status != 200:
                        return False, f"RSI server returned an unexpected error (HTTP {response.status})."

                    html_content = await response.text()
                    soup = BeautifulSoup(html_content, "html.parser")

                    # Target the bio container. RSI structure places bio text inside a div with class 'value'
                    value_divs = soup.find_all("div", class_="value")

                    bio_text = ""
                    code_found = False
                    for div in value_divs:
                        text = div.get_text(strip=True)
                        if code in text:
                            code_found = True
                            break
                        bio_text += " " + text

                    if not code_found:
                        return False, (
                            "The code was not found in your Short Bio. Sometimes RSI caches profiles—"
                            "wait a minute and try again."
                        )

                    # Extract main org if code is found
                    org_link = soup.select_one(".main-org .info .entry a.value")
                    org = ""
                    if org_link and "href" in org_link.attrs:
                        href = org_link["href"]
                        if isinstance(href, str):
                            org = href.split("/")[-1].upper()
                    if not org:
                        org = None

                    return True, {"message": "Code successfully validated against the bio!", "org": org}

            except Exception as e:
                return False, f"Scraping error: {str(e)}"

    async def _check_org_status(self, handle: str, target_org: str) -> tuple[str, str]:
        """Return (status, rank) based on the RSI profile.
        Status is 'Main', 'Affiliate', 'None', or 'Error'.
        Rank is the organization rank string or 'None'/'Error'.
        """
        url_main = f"https://robertsspaceindustries.com/citizens/{handle}"
        url_orgs = f"https://robertsspaceindustries.com/citizens/{handle}/organizations"

        # If no target org is provided, we default to no relationship.
        if not target_org:
            return "None", "None"

        async with aiohttp.ClientSession() as session:
            try:
                # 1. Check Main Org
                async with session.get(url_main) as response:
                    if response.status == 404:
                        return "None", "None"
                    elif response.status != 200:
                        return "Error", "Error"

                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")
                    org_link = soup.select_one(".main-org .info .entry a.value")
                    main_org = ""
                    if org_link and "href" in org_link.attrs:
                        href = org_link["href"]
                        if isinstance(href, str):
                            main_org = href.split("/")[-1]

                    if target_org.lower() == main_org.lower():
                        rank = "None"
                        for entry in soup.select(".main-org .info .entry"):
                            label = entry.select_one(".label")
                            if label and "Organization rank" in label.text:
                                value = entry.select_one(".value")
                                if value:
                                    rank = value.text.strip()
                                    break
                        return "Main", rank

                # 2. Check Affiliates
                async with session.get(url_orgs) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")
                        org_links = soup.find_all("a", href=True)
                        for link in org_links:
                            href = link.get("href")
                            if isinstance(href, str) and f"/orgs/{target_org}".lower() in href.lower():
                                # Affiliate rank is generally not on the orgs page easily without further scraping,
                                # we will just return None for affiliate rank for now.
                                return "Affiliate", "None"

            except Exception as e:
                print(f"Error checking org status: {e}")
                return "Error", "Error"
        return "None", "None"

    def _generate_code(self, org: str | None) -> str:
        # e.g., VER-SCANZ-A7K9 or just "VER-XXXX"; include org for clarity
        suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
        # prefix with org symbol if available
        return f"{org}-{suffix}" if org else f"VER-{suffix}"

    @app_commands.command(name="verify", description="Link your Discord account to your RSI Handle.")
    @app_commands.describe(handle="Your exact Star Citizen RSI Handle")
    @app_commands.describe(org="The organisation/affiliate you belong to")
    @app_commands.autocomplete(org=org_autocomplete)
    async def verify(self, interaction: discord.Interaction, handle: str, org: str | None = None):
        # ensure there is at least one configured org
        orgs = self._get_orgs()
        if not orgs:
            await interaction.response.send_message(
                "❌ No organisations configured. Please ask an administrator to add one.",
                ephemeral=True,
            )
            return

        # choose which org this verification is for
        if org:
            if org.upper() not in orgs:
                await interaction.response.send_message(
                    f"❌ Unknown organisation `{org}`. Valid choices: {', '.join(orgs)}.",
                    ephemeral=True,
                )
                return
            chosen_org = org.upper()
        else:
            # default to first configured org
            chosen_org = orgs[0]

        # 1. Check if they are already verified for this org
        existing_handle = self._is_verified(interaction.user.id, chosen_org)
        if existing_handle:
            await interaction.response.send_message(
                f"You are already verified for {chosen_org} and linked to the RSI Handle "
                f"**{existing_handle}**.",
                ephemeral=True,
            )
            return

        # 2. Generate a challenge code
        code = self._generate_code(chosen_org)

        # 3. Present the challenge to the user
        embed = discord.Embed(
            title="RSI Account Verification",
            description=(
                f"To securely link your Discord account to the RSI Handle **{handle}**, "
                "please follow these steps:\n\n"
                "1. Go to your [RSI Account Profile](https://robertsspaceindustries.com/account/profile).\n"
                "2. Add the unique code below to the **END** of your **Short Bio**.\n"
                "3. Click **'Apply All Changes'** at the bottom of the RSI page.\n"
                "4. Click the **'Verify Now'** button below."
            ),
            color=discord.Color.blue(),
        )
        embed.add_field(name="Your Unique Code", value=f"`{code}`", inline=False)
        embed.set_footer(text="You can remove the code from your bio once verification is successful.")

        view = VerifyNowView(self, handle, code, org=chosen_org)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(
        name="set_staff_role",
        description="Admin only: Set the role that can use staff commands (e.g. enforce, verify, suggestions).",
    )
    @app_commands.describe(role="The role that can use staff commands (e.g. Custodian).")
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(
        lambda i: i.user and isinstance(i.user, discord.Member) and i.user.guild_permissions.administrator
    )
    async def set_staff_role(self, interaction: discord.Interaction, role: discord.Role):
        """Set the staff role. Only users with Administrator can run this."""
        self._set_config("staff_role_id", str(role.id))
        await interaction.response.send_message(
            f"✅ Staff role set to {role.mention}. Users with this role or Administrator can use staff commands.",
            ephemeral=True,
        )

        # Log admin action
        embed = discord.Embed(
            title="Log Configuration Updated",
            description=(
                f"**Action:** Staff Role set to {role.mention}\n**Staff:** {interaction.user.mention}"
            ),
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )
        await self.bot.log_admin_action(embed)

    @app_commands.command(
        name="clear_staff_role",
        description="Admin only: Clear the staff role so only Administrator can use staff commands.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(
        lambda i: i.user and isinstance(i.user, discord.Member) and i.user.guild_permissions.administrator
    )
    async def clear_staff_role(self, interaction: discord.Interaction):
        """Clear the staff role. Only users with Administrator can run this."""
        self._set_config("staff_role_id", "")
        await interaction.response.send_message(
            "✅ Staff role cleared. Only users with Administrator can use staff commands.",
            ephemeral=True,
        )

        # Log admin action
        embed = discord.Embed(
            title="Log Configuration Updated",
            description=f"**Action:** Staff Role **CLEARED**\n**Staff:** {interaction.user.mention}",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )
        await self.bot.log_admin_action(embed)

    @app_commands.command(
        name="set_main_role", description="Set the role granted to verified Main Org members."
    )
    @app_commands.describe(role="The role to grant verified members (e.g. SCANZ Member).")
    @app_commands.check(has_staff_or_admin)
    async def set_main_role(self, interaction: discord.Interaction, role: discord.Role):
        self._set_config("main_role_id", str(role.id))
        await interaction.response.send_message(
            f"✅ Main role successfully set to {role.mention}.", ephemeral=True
        )

        # Log admin action
        embed = discord.Embed(
            title="Log Configuration Updated",
            description=f"**Action:** Main role set to {role.mention}\n**Staff:** {interaction.user.mention}",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )
        await self.bot.log_admin_action(embed)

    @app_commands.command(name="set_affiliate_role", description="Set the role granted to Affiliate members.")
    @app_commands.describe(role="The role to grant verified affiliates.")
    @app_commands.check(has_staff_or_admin)
    async def set_affiliate_role(self, interaction: discord.Interaction, role: discord.Role):
        self._set_config("affiliate_role_id", str(role.id))
        await interaction.response.send_message(
            f"✅ Affiliate role successfully set to {role.mention}.", ephemeral=True
        )

        # Log admin action
        embed = discord.Embed(
            title="Log Configuration Updated",
            description=(
                f"**Action:** Affiliate role set to {role.mention}\n**Staff:** {interaction.user.mention}"
            ),
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )
        await self.bot.log_admin_action(embed)

    @app_commands.command(
        name="set_guest_role", description="Set the role granted to verified Honored Guests."
    )
    @app_commands.describe(role="The role to grant to non-org verified users.")
    @app_commands.check(has_staff_or_admin)
    async def set_guest_role(self, interaction: discord.Interaction, role: discord.Role):
        self._set_config("guest_role_id", str(role.id))
        await interaction.response.send_message(
            f"✅ Honored Guest role successfully set to {role.mention}.", ephemeral=True
        )

    @app_commands.command(
        name="set_unverified_role", description="Set the role applied to users needing verification."
    )
    @app_commands.describe(role="The role (e.g. Needs Verification) for unverified users.")
    @app_commands.check(has_staff_or_admin)
    async def set_unverified_role(self, interaction: discord.Interaction, role: discord.Role):
        self._set_config("unverified_role_id", str(role.id))
        await interaction.response.send_message(
            f"✅ Unverified role successfully set to {role.mention}.", ephemeral=True
        )

        # Log admin action
        embed = discord.Embed(
            title="Log Configuration Updated",
            description=(
                f"**Action:** Unverified role set to {role.mention}\n**Staff:** {interaction.user.mention}"
            ),
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )
        await self.bot.log_admin_action(embed)

    @app_commands.command(
        name="manual_verify",
        description="Manually initiate verification for a specific member.",
    )
    @app_commands.describe(member="The Discord member", handle="The RSI Handle to link")
    @app_commands.describe(org="Organisation symbol for this manual verification")
    @app_commands.check(has_staff_or_admin)
    @app_commands.autocomplete(org=org_autocomplete)
    async def manual_verify(
        self, interaction: discord.Interaction, member: discord.Member, handle: str, org: str | None = None
    ):
        # Determine organisation for manual verification
        orgs = self._get_orgs()
        chosen_org = None
        if org:
            if org.upper() in orgs:
                chosen_org = org.upper()
            else:
                await interaction.response.send_message(
                    f"❌ Unknown organisation `{org}`. Valid: {', '.join(orgs)}.",
                    ephemeral=True,
                )
                return
        else:
            chosen_org = orgs[0] if orgs else None

        # Generate challenge code
        code = self._generate_code(chosen_org)

        embed = discord.Embed(
            title="Manual Verification Initiated",
            description=(
                f"You are initiating manual verification for {member.mention} with RSI Handle "
                f"**{handle}**.\n\n"
                f"1. Ask the user to add `{code}` to their RSI Short Bio.\n"
                "2. Click the button below once they have done so."
            ),
            color=discord.Color.blue(),
        )
        embed.set_footer(text=f"Target: {member.name} | Handle: {handle}")

        # Reusing VerifyNowView logic but adapted for manual flow
        class ManualVerifyView(discord.ui.View):
            def __init__(self, cog, target_member, target_handle, target_code, target_org=None):
                super().__init__(timeout=None)
                self.cog = cog
                self.member = target_member
                self.handle = target_handle
                self.code = target_code
                self.org = target_org

            @discord.ui.button(label="Complete Verification", style=discord.ButtonStyle.success, emoji="✅")
            async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.defer(ephemeral=True)
                success, message = await self.cog._scrape_rsi_bio(self.handle, self.code)

                if success:
                    target_org = self.org
                    if not target_org and isinstance(message, dict):
                        target_org = message.get("org")

                    org_status, org_rank = await self.cog._check_org_status(self.handle, target_org)

                    self.cog._link_account(
                        self.member.id,
                        self.handle,
                        target_org,
                        org_status,
                        org_rank,
                    )

                    # sync roles (will add verified role and remove needs-role)
                    await self.cog.sync_member_roles(self.member)

                    # Log admin action
                    embed = discord.Embed(
                        title="Manual Verification Completed",
                        description=(
                            f"**Member:** {self.member.mention} ({self.member.id})\n"
                            f"**RSI Handle:** `{self.handle}`\n"
                            f"**Org:** `{target_org}`\n"
                            f"**Staff:** {interaction.user.mention}"
                        ),
                        color=discord.Color.green(),
                        timestamp=discord.utils.utcnow(),
                    )
                    await self.cog.bot.log_admin_action(embed)

                    await interaction.followup.send(
                        f"✅ Successfully verified and linked {self.member.mention} to `{self.handle}`.",
                        ephemeral=True,
                    )
                    self.stop()
                else:
                    await interaction.followup.send(f"❌ Verification failed: {message}", ephemeral=True)

        # create view with selected organisation and send once
        view = ManualVerifyView(self, member, handle, code, target_org=chosen_org)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(
        name="export_verified",
        description="Export the verification database to a CSV file.",
    )
    @app_commands.check(has_staff_or_admin)
    async def export_verified(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # check if org_rank exists
            cursor.execute("PRAGMA table_info(rsi_links)")
            if "org_rank" in [c[1] for c in cursor.fetchall()]:
                cursor.execute(
                    "SELECT discord_id, rsi_handle, org_handle, org_status, org_rank FROM rsi_links"
                )
            else:
                cursor.execute("SELECT discord_id, rsi_handle, org_handle, org_status, 'None' FROM rsi_links")
            rows = cursor.fetchall()

        if not rows:
            await interaction.followup.send("The verification database is empty.", ephemeral=True)
            return

        # Use in-memory buffer for CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Discord ID", "Discord Name", "RSI Handle", "Org", "Org Status", "Org Rank"])

        for discord_id, rsi_handle, org, status, rank in rows:
            # Try to resolve member name for readability in CSV
            member = interaction.guild.get_member(discord_id)
            name = f"{member.name}" if member else "Unknown/Left"
            writer.writerow([discord_id, name, rsi_handle, org, status, rank])

        output.seek(0)
        file = discord.File(io.BytesIO(output.getvalue().encode()), filename="verified_members.csv")

        await interaction.followup.send(
            f"✅ Exported {len(rows)} verified members.", file=file, ephemeral=True
        )

    @app_commands.command(
        name="export_unverified",
        description="Export a list of members who are not verified to a CSV file.",
    )
    @app_commands.describe(role="Optional: Only include unverified members who have this role.")
    @app_commands.check(has_staff_or_admin)
    async def export_unverified(self, interaction: discord.Interaction, role: discord.Role | None = None):
        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT discord_id FROM rsi_links")
            verified_ids = {row[0] for row in cursor.fetchall()}

        # Filter members in the guild who are not verified
        unverified_members = []
        for member in interaction.guild.members:
            if member.bot:
                continue
            if role and role not in member.roles:
                continue
            if member.id not in verified_ids:
                unverified_members.append(member)

        if not unverified_members:
            if not role:
                message = "All members are verified!"
            else:
                message = f"All members with the {role.mention} role are verified!"
            await interaction.followup.send(message, ephemeral=True)
            return

        # Use in-memory buffer for CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Discord ID", "Discord Name", "Joined Server At"])

        for member in unverified_members:
            joined_at = member.joined_at.strftime("%Y-%m-%d %H:%M:%S") if member.joined_at else "Unknown"
            writer.writerow([member.id, member.name, joined_at])

        output.seek(0)
        file_name = "unverified_members.csv" if not role else f"unverified_members_{role.name}.csv"
        file = discord.File(io.BytesIO(output.getvalue().encode()), filename=file_name)

        await interaction.followup.send(
            f"✅ Exported {len(unverified_members)} unverified members.", file=file, ephemeral=True
        )

    @app_commands.command(
        name="search_verified",
        description="Search for a verified member by Handle or Discord ID.",
    )
    @app_commands.describe(query="RSI Handle, Discord ID, or Mention")
    @app_commands.check(has_staff_or_admin)
    async def search_verified(self, interaction: discord.Interaction, query: str):
        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        # Cleanup query (mentions, etc)
        clean_query = query.replace("<@", "").replace(">", "").replace("!", "")

        # Escape wildcard characters for LIKE query
        escaped_query = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(rsi_links)")
            has_rank = "org_rank" in [c[1] for c in cursor.fetchall()]

            if has_rank:
                cursor.execute(
                    "SELECT discord_id, rsi_handle, org_handle, org_status, org_rank FROM rsi_links"
                    " WHERE rsi_handle LIKE ? ESCAPE '\\' OR discord_id = ?",
                    (f"%{escaped_query}%", clean_query if clean_query.isdigit() else 0),
                )
            else:
                cursor.execute(
                    "SELECT discord_id, rsi_handle, org_handle, org_status, 'None' FROM rsi_links"
                    " WHERE rsi_handle LIKE ? ESCAPE '\\' OR discord_id = ?",
                    (f"%{escaped_query}%", clean_query if clean_query.isdigit() else 0),
                )
            rows = cursor.fetchall()

        if not rows:
            await interaction.response.send_message(f"No results found for `{query}`.", ephemeral=True)
            return

        embed = discord.Embed(title="Verification Search Results", color=discord.Color.blue())
        for discord_id, rsi_handle, org, status, rank in rows[:10]:  # Limit to 10 for sanity
            member = interaction.guild.get_member(discord_id)
            mention = member.mention if member else f"ID: {discord_id} (Left Server)"

            value_text = f"User: {mention}\nStatus: {status}"
            if rank and rank != "None":
                value_text += f"\nRank: {rank}"

            embed.add_field(name=f"{rsi_handle} ({org})", value=value_text, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="grant_verified",
        description="Manually grant the verified role and RSI nickname to a member.",
    )
    @app_commands.describe(member="The Discord member to grant the verified role to.")
    @app_commands.check(has_staff_or_admin)
    async def grant_verified(self, interaction: discord.Interaction, member: discord.Member):
        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        # allow grant to specify org? use any for now
        rsi_handle = self._is_verified(member.id)
        if not rsi_handle:
            await interaction.response.send_message(
                f"❌ **{member.mention}** is not verified in the database. "
                "They must complete `/verify` first.",
                ephemeral=True,
            )
            return

        messages = []

        # Apply role based on status (but since this is manual, default to Guest or fetch status)
        org_status = "Guest"
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT org_status FROM rsi_links WHERE discord_id = ?", (member.id,))
            row = cursor.fetchone()
            if row and row[0]:
                org_status = row[0]

        # We try to apply the correct role mapping
        if org_status == "Main":
            role_id_str = self._get_config("main_role_id")
        elif org_status == "Affiliate":
            role_id_str = self._get_config("affiliate_role_id")
        else:
            role_id_str = self._get_config("guest_role_id")
        if role_id_str:
            verified_role = interaction.guild.get_role(int(role_id_str))
            if verified_role:
                try:
                    await member.add_roles(verified_role)
                    messages.append(f"✅ Granted role {verified_role.mention}.")
                except discord.Forbidden:
                    messages.append(f"⚠️ Could not assign role `{verified_role.name}` (permission denied).")
            else:
                messages.append("⚠️ Configured role not found in server — check settings.")
        else:
            messages.append(f"⚠️ No appropriate role configured for status: {org_status}.")

        await interaction.response.send_message(
            f"**Grant Verified: {member.display_name}** (`{rsi_handle}`)\n" + "\n".join(messages),
            ephemeral=True,
        )

    # helper to sync a member's roles based on their verification state
    async def sync_member_roles(self, member: discord.Member) -> None:
        guild = member.guild
        scanz_role = guild.get_role(int(self._get_config("scanz_role_id") or 0))

        main_role = guild.get_role(int(self._get_config("main_role_id") or 0))
        affiliate_role = guild.get_role(int(self._get_config("affiliate_role_id") or 0))
        guest_role = guild.get_role(int(self._get_config("guest_role_id") or 0))
        unverified_role = guild.get_role(int(self._get_config("unverified_role_id") or 0))

        # Check Verification DB
        org_status = None
        has_rsi_linked = False
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT org_status FROM rsi_links WHERE discord_id = ?", (member.id,))
            row = cursor.fetchone()
            if row:
                has_rsi_linked = True
                org_status = row[0]

        to_add, to_remove = [], []

        # Start with all org-related roles they currently have
        all_possible_roles = [
            r for r in [main_role, affiliate_role, guest_role, unverified_role] if r is not None
        ]

        if has_rsi_linked:
            # Verified User - Ensure they get the role matching their status
            target_role = guest_role
            if org_status == "Main":
                target_role = main_role
            elif org_status == "Affiliate":
                target_role = affiliate_role

            for r in all_possible_roles:
                if r == target_role and r not in member.roles:
                    to_add.append(r)
                elif r != target_role and r in member.roles:
                    to_remove.append(r)
        else:
            # Unverified User - strip org roles. Only give them unverified role
            # if they have the 'SCANZ identifier' role or if server configured it.
            for r in all_possible_roles:
                if r == unverified_role:
                    if scanz_role and scanz_role in member.roles and r not in member.roles:
                        to_add.append(r)
                else:
                    if r in member.roles:
                        to_remove.append(r)

            # If no SCANZ identifier role exists, but they are unverified, give them unverified role.
            if not scanz_role and unverified_role and unverified_role not in member.roles:
                to_add.append(unverified_role)

        if to_add:
            try:
                await member.add_roles(*to_add, reason="Verification sync")
            except discord.Forbidden:
                pass
        if to_remove:
            try:
                await member.remove_roles(*to_remove, reason="Verification sync")
            except discord.Forbidden:
                pass

    # configuration commands
    @app_commands.command(name="add_org", description="Add an RSI organisation/affiliate symbol")
    @app_commands.describe(symbol="The RSI org symbol, e.g. SCANZ")
    @app_commands.check(has_staff_or_admin)
    async def add_org(self, interaction: discord.Interaction, symbol: str):
        added = self._add_org(symbol)
        if added:
            await interaction.response.send_message(
                f"✅ Added organisation `{symbol.upper()}`.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"ℹ️ `{symbol.upper()}` is already configured.", ephemeral=True
            )

    @app_commands.command(name="remove_org", description="Remove an RSI organisation/affiliate symbol")
    @app_commands.describe(symbol="The RSI org symbol to remove")
    @app_commands.check(has_staff_or_admin)
    async def remove_org(self, interaction: discord.Interaction, symbol: str):
        removed = self._remove_org(symbol)
        if removed:
            await interaction.response.send_message(
                f"✅ Removed organisation `{symbol.upper()}`.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"⚠️ `{symbol.upper()}` was not configured.", ephemeral=True
            )

    @app_commands.command(name="list_orgs", description="List configured RSI organisations/affiliates.")
    async def list_orgs(self, interaction: discord.Interaction):
        orgs = self._get_orgs()
        if orgs:
            await interaction.response.send_message(
                "Configured organisations: " + ", ".join(orgs), ephemeral=True
            )
        else:
            await interaction.response.send_message("No organisations have been added yet.", ephemeral=True)

    @app_commands.command(
        name="set_scanz_role", description="Set the role that identifies SCANZ members (optional filter)."
    )
    @app_commands.describe(role="Role that members should have to trigger unverified checks")
    @app_commands.check(has_staff_or_admin)
    async def set_scanz_role(self, interaction: discord.Interaction, role: discord.Role):
        self._set_config("scanz_role_id", str(role.id))
        await interaction.response.send_message(f"✅ Filter role set to {role.mention}.", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # Only process if the nickname actually changed
        if before.nick == after.nick:
            return

        # Check if the user is verified
        rsi_handle = self._is_verified(after.id)
        if not rsi_handle:
            return

        current_nick = after.nick or after.name

        # "Fuzzy" allow rule: the nickname must *contain* the exact RSI handle (case-insensitive).
        # This allows things like "[SCANZ] Handle" or "Handle (Bob)".
        if rsi_handle.lower() not in current_nick.lower():
            try:
                # If they completely changed it and it doesn't contain handle, force it to just the handle
                await after.edit(nick=rsi_handle)
            except discord.Forbidden:
                pass


async def setup(bot):
    await bot.add_cog(RSIVerification(bot))
