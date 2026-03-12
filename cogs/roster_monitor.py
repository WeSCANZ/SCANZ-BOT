import asyncio
import sqlite3
import typing
from datetime import datetime, timezone
from typing import List, Optional, Tuple

import aiohttp
import discord
from bs4 import BeautifulSoup
from discord import app_commands
from discord.ext import commands, tasks

from utils.checks import has_staff_or_admin


async def org_autocomplete(interaction: discord.Interaction, current: str):
    bot = typing.cast(commands.Bot, interaction.client)
    cog = typing.cast(typing.Any, bot.get_cog("RSIVerification"))
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

    async def cog_unload(self):
        self.roster_check_loop.cancel()

    def _get_verified_links(self):
        """Fetch all links including organisation info."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT discord_id, rsi_handle, org_handle, org_status FROM rsi_links")
                return cursor.fetchall()
        except sqlite3.OperationalError:
            print("[RosterMonitor] Error: rsi_links table not found.")
            return []

    def _get_config(self, key: str) -> Optional[str]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM rsi_config WHERE key = ?", (key,))
                row = cursor.fetchone()
                return str(row[0]) if row else None
        except sqlite3.OperationalError:
            print("[RosterMonitor] Error: rsi_config table not found.")
            return None

    def _set_config(self, key: str, value: str):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR REPLACE INTO rsi_config (key, value) VALUES (?, ?)", (key, value))
                conn.commit()
        except sqlite3.OperationalError as e:
            print(f"[RosterMonitor] DB Error setting config: {e}")

    async def _check_org_membership(self, handle: str, org: str) -> Tuple[bool, str]:
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
                        href = link.get("href")
                        if isinstance(href, str) and f"/orgs/{org}".lower() in href.lower():
                            return True, "Member"

                    return False, "Not in Org"
            except Exception as e:
                return False, f"Error: {str(e)}"

    async def _fetch_all_org_members(self, org: str) -> List[str]:
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

        # Ensure the RSIVerification cog is loaded to guarantee database schema exists
        if not self.bot.get_cog("RSIVerification"):
            print("[RosterMonitor] RSIVerification cog is not loaded. Skipping audit.")
            return

        await self._run_audit()

    async def _run_audit(self, trigger_interaction: Optional[discord.Interaction] = None):
        """Execute the audit logic and notify admins for each configured org."""
        target_channel_id = self._get_config("roster_audit_channel")
        if not target_channel_id:
            if trigger_interaction:
                await trigger_interaction.followup.send(
                    "❌ Audit channel not set. Use `/set_roster_channel`.", ephemeral=True
                )
            return

        target_channel = self.bot.get_channel(int(target_channel_id))
        if not isinstance(target_channel, discord.TextChannel):
            return

        verified_members = self._get_verified_links()
        if trigger_interaction:
            await trigger_interaction.followup.send("🔄 Syncing roles for guild members...", ephemeral=True)
        # run role synchronization for everyone who has the SCANZ role; this will
        # mark unverified members with the needs-verification role and clean up
        # anyone who recently became verified.
        cog = typing.cast(typing.Any, self.bot.get_cog("RSIVerification"))
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
        for discord_id, handle, org, current_status in verified_members:
            cog = typing.cast(typing.Any, self.bot.get_cog("RSIVerification"))
            
            # Scrape new status via the new _check_org_status logic in verification cog
            new_status = "None"
            if cog:
                new_status = await cog._check_org_status(handle, org)
            
            # Did their status change?
            if new_status and new_status != current_status:
                try:
                    with sqlite3.connect(self.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE rsi_links SET org_status = ? WHERE discord_id = ?",
                            (new_status, discord_id)
                        )
                        conn.commit()
                except Exception as e:
                    print(f"Failed to update org_status for {discord_id}: {e}")

                audit_results.append((
                    discord_id, handle, org, f"Status changed: {current_status} -> {new_status}"
                ))

                # Re-sync their roles now that DB is updated
                member = target_channel.guild.get_member(discord_id)
                if member and cog:
                    await cog.sync_member_roles(member)

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

            admin_role_id = self._get_config("main_role_id")
            content = f"<@&{admin_role_id}> Roster audit complete." if admin_role_id else None

            await target_channel.send(content=content, embed=embed)

        if trigger_interaction:
            await trigger_interaction.followup.send(
                "✅ Audit complete! Results sent to the audit channel.", ephemeral=True
            )

    @app_commands.command(
        name="set_roster_channel", description="Set the channel for roster audit notifications."
    )
    @app_commands.check(has_staff_or_admin)
    async def set_roster_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self._set_config("roster_audit_channel", str(channel.id))
        await interaction.response.send_message(
            f"✅ Roster audit channel set to {channel.mention}.", ephemeral=True
        )

    @app_commands.command(
        name="roster_audit",
        description="Manually trigger a check of all verified members' Org status.",
    )
    @app_commands.check(has_staff_or_admin)
    async def roster_audit(self, interaction: discord.Interaction):
        if not self.bot.get_cog("RSIVerification"):
            await interaction.response.send_message(
                "❌ RSIVerification cog is not loaded. Required for database access.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        await self._run_audit(interaction)

    @app_commands.command(
        name="org_full_sync",
        description="Sync one or all RSI Org rosters with the verification database.",
    )
    @app_commands.describe(org="The organisation symbol to sync (optional)")
    @app_commands.autocomplete(org=org_autocomplete)
    @app_commands.check(has_staff_or_admin)
    async def org_full_sync(self, interaction: discord.Interaction, org: Optional[str] = None):
        """Perform a full synchronization check between RSI and Discord.

        If `org` is provided we only sync that symbol; otherwise all configured orgs are scanned.
        """
        if not self.bot.get_cog("RSIVerification"):
            await interaction.response.send_message(
                "❌ RSIVerification cog is not loaded. Required for database access.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        verified_links = self._get_verified_links()
        verified_handles = {h.lower() for _, h, _ in verified_links}

        # determine which org(s) to operate on
        orgs = []
        cog = typing.cast(typing.Any, self.bot.get_cog("RSIVerification"))
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
