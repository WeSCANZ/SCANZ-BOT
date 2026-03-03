import asyncio
import sqlite3
from datetime import datetime, timezone

import aiohttp
import discord
from bs4 import BeautifulSoup
from discord import app_commands
from discord.ext import commands, tasks


async def org_autocomplete(interaction: discord.Interaction, current: str):
    cog = interaction.client.get_cog("RSIVerification")
    if not cog:
        return []
    orgs = cog._get_orgs()
    return [app_commands.Choice(name=o, value=o) for o in orgs if current.lower() in o.lower()]


class RosterMonitor(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_path = "data/enforcer.db"
        # the list of organisations will be retrieved from the verification cog
        self.roster_check_loop.start()

    def cog_unload(self):
        self.roster_check_loop.cancel()

    def _get_verified_links(self):
        """Fetch all links including organisation info."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT discord_id, rsi_handle, org_handle FROM rsi_links")
            return cursor.fetchall()

    def _get_config(self, key: str) -> str:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM rsi_config WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else None

    def _set_config(self, key: str, value: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO rsi_config (key, value) VALUES (?, ?)", (key, value))
            conn.commit()

    async def _check_org_membership(self, handle: str, org: str) -> tuple[bool, str]:
        """Scrape rsi profile to check if user is in the given organisation."""
        url = f"https://robertsspaceindustries.com/citizens/{handle}/organizations"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        return False, f"HTTP Error {response.status}"

                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")

                    # Look for org links. Usually orgs are linked as /orgs/ORG_HANDLE
                    org_links = soup.find_all("a", href=True)
                    for link in org_links:
                        if f"/orgs/{org}".lower() in link["href"].lower():
                            return True, "Member"

                    return False, "Not in Org"
            except Exception as e:
                return False, f"Error: {str(e)}"

    async def _fetch_all_org_members(self, org: str) -> list[str]:
        """Scrape the entire RSI organisation roster for a given org and return handles."""
        api_url = "https://robertsspaceindustries.com/api/orgs/getOrgMembers"
        headers = {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"https://robertsspaceindustries.com/orgs/{org}/members",
        }

        handles = []
        page = 1
        page_size = 32

        async with aiohttp.ClientSession(headers=headers) as session:
            while True:
                payload = {
                    "symbol": org,
                    "search": "",
                    "pagesize": page_size,
                    "page": page,
                }
                try:
                    async with session.post(api_url, json=payload) as response:
                        if response.status != 200:
                            print(f"[RosterSync] Error: API returned {response.status}")
                            break

                        data = await response.json()
                        if not data.get("success") or "data" not in data:
                            break

                        html = data["data"].get("html", "")
                        if not html:
                            break

                        soup = BeautifulSoup(html, "html.parser")
                        nicks = soup.select(".nick")
                        if not nicks:
                            break

                        for nick in nicks:
                            handle = nick.get_text(strip=True)
                            if handle:
                                handles.append(handle)

                        total_rows = data["data"].get("totalrows", 0)
                        if len(handles) >= total_rows:
                            break

                        page += 1
                        await asyncio.sleep(1)

                except Exception as e:
                    print(f"[RosterSync] Scraping exception: {e}")
                    break

        return list(set(handles))

    @tasks.loop(hours=168)  # 1 week
    async def roster_check_loop(self):
        """Weekly background task to audit all configured organisations."""
        await self.bot.wait_until_ready()
        await self._run_audit()

    async def _run_audit(self, trigger_interaction: discord.Interaction = None):
        """Execute the audit logic and notify admins for each configured org."""
        target_channel_id = self._get_config("roster_audit_channel")
        if not target_channel_id:
            if trigger_interaction:
                await trigger_interaction.followup.send(
                    "❌ Audit channel not set. Use `/set_roster_channel`.", ephemeral=True
                )
            return

        target_channel = self.bot.get_channel(int(target_channel_id))
        if not target_channel:
            return

        verified_members = self._get_verified_links()
        if trigger_interaction:
            await trigger_interaction.followup.send("🔄 Syncing roles for guild members...", ephemeral=True)
        # run role synchronization for everyone who has the SCANZ role; this will
        # mark unverified members with the needs-verification role and clean up
        # anyone who recently became verified.
        cog = self.bot.get_cog("RSIVerification")
        if cog:
            scanz_role_id = cog._get_config("scanz_role_id")
            if scanz_role_id:
                scanz_role = target_channel.guild.get_role(int(scanz_role_id))
                if scanz_role:
                    for member in scanz_role.members:
                        await cog.sync_member_roles(member)
                        await asyncio.sleep(0.5)

        if not verified_members:
            if trigger_interaction:
                await trigger_interaction.followup.send(
                    "No verified members found in database.", ephemeral=True
                )
            return

        if trigger_interaction:
            await trigger_interaction.followup.send(
                f"🔍 Starting roster audit for {len(verified_members)} entries...", ephemeral=True
            )

        audit_results = []
        # loop through each stored entry; entries include org value
        for discord_id, handle, org in verified_members:
            # sync discord roles if possible
            cog = self.bot.get_cog("RSIVerification")
            member = target_channel.guild.get_member(discord_id)
            if member and cog:
                await cog.sync_member_roles(member)

            is_member, status = await self._check_org_membership(handle, org)
            if not is_member:
                audit_results.append((discord_id, handle, org, status))
            await asyncio.sleep(2)

        if not audit_results:
            embed = discord.Embed(
                title="Roster Audit: Clean",
                description="✅ All verified members are still active in their configured organisations.",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc),
            )
            await target_channel.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Roster Audit: Anomalies Found",
                description=(
                    f"⚠️ {len(audit_results)} entries reference handles no longer detected in their org.\n\n"
                    "Please review their roles manually."
                ),
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc),
            )

            anomalies_str = ""
            for d_id, handle, org, status in audit_results:
                line = f"- <@{d_id}> (`{handle}` in {org}): {status}\n"
                if len(anomalies_str) + len(line) > 1000:
                    embed.add_field(name="Anomaly List", value=anomalies_str, inline=False)
                    anomalies_str = line
                else:
                    anomalies_str += line

            if anomalies_str:
                embed.add_field(name="Anomaly List", value=anomalies_str, inline=False)

            admin_role_id = self._get_config("verified_role_id")
            content = f"<@&{admin_role_id}> Roster audit complete." if admin_role_id else None

            await target_channel.send(content=content, embed=embed)

        if trigger_interaction:
            await trigger_interaction.followup.send(
                "✅ Audit complete! Results sent to the audit channel.", ephemeral=True
            )

    @app_commands.command(
        name="set_roster_channel", description="Admin: Set the channel for roster audit notifications."
    )
    @app_commands.default_permissions(administrator=True)
    async def set_roster_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self._set_config("roster_audit_channel", str(channel.id))
        await interaction.response.send_message(
            f"✅ Roster audit channel set to {channel.mention}.", ephemeral=True
        )

    @app_commands.command(
        name="roster_audit",
        description="Admin: Manually trigger a check of all verified members' Org status.",
    )
    @app_commands.default_permissions(administrator=True)
    async def roster_audit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self._run_audit(interaction)

    @app_commands.command(
        name="org_full_sync",
        description="Admin: Sync one or all RSI Org rosters with the verification database.",
    )
    @app_commands.describe(org="The organisation symbol to sync (optional)")
    @app_commands.autocomplete(org=org_autocomplete)
    @app_commands.default_permissions(administrator=True)
    async def org_full_sync(self, interaction: discord.Interaction, org: str = None):
        """Perform a full synchronization check between RSI and Discord.

        If `org` is provided we only sync that symbol; otherwise all configured orgs are scanned.
        """
        await interaction.response.defer(ephemeral=True)

        verified_links = self._get_verified_links()
        verified_handles = {h.lower() for _, h, _ in verified_links}

        # determine which org(s) to operate on
        orgs = []
        cog = self.bot.get_cog("RSIVerification")
        if cog:
            orgs = cog._get_orgs()
        if org:
            if org.upper() not in orgs:
                await interaction.followup.send(
                    f"❌ Unknown org `{org}`. Valid: {', '.join(orgs)}.", ephemeral=True
                )
                return
            orgs = [org.upper()]

        if not orgs:
            await interaction.followup.send("❌ No organisations configured.", ephemeral=True)
            return

        await interaction.followup.send(
            f"📥 Fetching members for {', '.join(orgs)} from RSI (this may take a minute)...", ephemeral=True
        )

        missing_from_db = []
        for symbol in orgs:
            rsi_handles = await self._fetch_all_org_members(symbol)
            if not rsi_handles:
                await interaction.followup.send(
                    f"❌ Error: Could not fetch members from RSI for {symbol}.", ephemeral=True
                )
                continue

            for h in rsi_handles:
                if h.lower() not in verified_handles:
                    missing_from_db.append((h, symbol))

        embed = discord.Embed(
            title="Full Org Sync",
            description=("Comparison complete between RSI members and verified database entries."),
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc),
        )

        stats = {symbol: 0 for symbol in orgs}
        for _, symbol in missing_from_db:
            stats[symbol] += 1

        embed.add_field(
            name="Unverified totals", value="\n".join(f"{s}: {stats[s]}" for s in stats), inline=False
        )

        if missing_from_db:
            missing_str = "\n".join([f"- `{h}` ({sym})" for h, sym in missing_from_db[:30]])
            if len(missing_from_db) > 30:
                missing_str += f"\n*...and {len(missing_from_db) - 30} more.*"
            embed.add_field(name="Unlinked RSI Members", value=missing_str, inline=False)
        else:
            embed.add_field(
                name="Unlinked RSI Members",
                value="✅ All RSI members are verified in the database!",
                inline=False,
            )

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(RosterMonitor(bot))
