import asyncio
import sqlite3
from datetime import datetime

import aiohttp
import discord
from bs4 import BeautifulSoup
from discord import app_commands
from discord.ext import commands, tasks


class RosterMonitor(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_path = "data/enforcer.db"
        self.org_handle = "SCANZ"  # The RSI Org handle to check for
        self.roster_check_loop.start()

    def cog_unload(self):
        self.roster_check_loop.cancel()

    def _get_verified_links(self):
        """Fetch all discord_id to rsi_handle mappings."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT discord_id, rsi_handle FROM rsi_links")
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

    async def _check_org_membership(self, handle: str) -> tuple[bool, str]:
        """Scrape rsi profile to check if user is in the specified organization."""
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
                        if f"/orgs/{self.org_handle}".lower() in link["href"].lower():
                            return True, "Member"

                    return False, "Not in Org"
            except Exception as e:
                return False, f"Error: {str(e)}"

    async def _fetch_all_org_members(self) -> list[str]:
        """Scrape the entire RSI organization roster and return a list of handles."""
        api_url = "https://robertsspaceindustries.com/api/orgs/getOrgMembers"
        headers = {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"https://robertsspaceindustries.com/orgs/{self.org_handle}/members",
        }

        handles = []
        page = 1
        page_size = 32

        async with aiohttp.ClientSession(headers=headers) as session:
            while True:
                payload = {
                    "symbol": self.org_handle,
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
                        # The subagent identified .nick as the handle container
                        nicks = soup.select(".nick")
                        if not nicks:
                            break

                        for nick in nicks:
                            handle = nick.get_text(strip=True)
                            if handle:
                                handles.append(handle)

                        # Check if we should continue
                        total_rows = data["data"].get("totalrows", 0)
                        if len(handles) >= total_rows:
                            break

                        page += 1
                        # Mitigation for rate limits
                        await asyncio.sleep(1)

                except Exception as e:
                    print(f"[RosterSync] Scraping exception: {e}")
                    break

        return list(set(handles))  # Ensure uniqueness

    @tasks.loop(hours=168)  # 1 week
    async def roster_check_loop(self):
        """Weekly background task to audit the organization roster."""
        # Wait until bot is ready
        await self.bot.wait_until_ready()
        await self._run_audit()

    async def _run_audit(self, trigger_interaction: discord.Interaction = None):
        """Execute the audit logic and notify admins."""
        target_channel_id = self._get_config("roster_audit_channel")
        if not target_channel_id:
            if trigger_interaction:
                await trigger_interaction.followup.send(
                    "❌ Audit channel not set. Use `/set_roster_channel`."
                )
            return

        target_channel = self.bot.get_channel(int(target_channel_id))
        if not target_channel:
            return

        verified_members = self._get_verified_links()
        if not verified_members:
            if trigger_interaction:
                await trigger_interaction.followup.send("No verified members found in database.")
            return

        if trigger_interaction:
            await trigger_interaction.followup.send(
                f"🔍 Starting roster audit for {len(verified_members)} members..."
            )

        audit_results = []
        for discord_id, handle in verified_members:
            is_member, status = await self._check_org_membership(handle)
            if not is_member:
                audit_results.append((discord_id, handle, status))
            # Rate limit mitigation
            await asyncio.sleep(2)

        if not audit_results:
            embed = discord.Embed(
                title="Roster Audit: Clean",
                description="✅ All verified members are still active in the SCANZ organization.",
                color=discord.Color.green(),
                timestamp=datetime.now(),
            )
            await target_channel.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Roster Audit: Anomalies Found",
                description=(
                    f"⚠️ {len(audit_results)} members are no longer detected in the "
                    f"**{self.org_handle}** organization.\n\nPlease review their roles manually."
                ),
                color=discord.Color.red(),
                timestamp=datetime.now(),
            )

            anomalies_str = ""
            for d_id, handle, status in audit_results:
                line = f"- <@{d_id}> (`{handle}`): {status}\n"
                if len(anomalies_str) + len(line) > 1000:
                    embed.add_field(name="Anomaly List", value=anomalies_str, inline=False)
                    anomalies_str = line
                else:
                    anomalies_str += line

            if anomalies_str:
                embed.add_field(name="Anomaly List", value=anomalies_str, inline=False)

            # Optional: Ping admin role if configured
            admin_role_id = self._get_config("verified_role_id")
            content = f"<@&{admin_role_id}> Roster audit complete." if admin_role_id else None

            await target_channel.send(content=content, embed=embed)

        if trigger_interaction:
            await trigger_interaction.followup.send("✅ Audit complete! Results sent to the audit channel.")

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
        description="Admin: Sync the entire RSI Org roster with the verification database.",
    )
    @app_commands.default_permissions(administrator=True)
    async def org_full_sync(self, interaction: discord.Interaction):
        """Perform a full synchronization check between RSI and Discord."""
        await interaction.response.defer(ephemeral=True)

        verified_links = self._get_verified_links()
        verified_handles = {h.lower() for _, h in verified_links}

        await interaction.followup.send(
            f"📥 Fetching all members from `{self.org_handle}` roster on RSI (this may take a minute)..."
        )

        rsi_handles = await self._fetch_all_org_members()
        if not rsi_handles:
            await interaction.followup.send("❌ Error: Could not fetch members from RSI.", ephemeral=True)
            return

        missing_from_db = []
        for h in rsi_handles:
            if h.lower() not in verified_handles:
                missing_from_db.append(h)

        embed = discord.Embed(
            title=f"Full Org Sync: {self.org_handle}",
            description=(
                f"Comparison complete between **{len(rsi_handles)}** RSI members "
                f"and **{len(verified_handles)}** verified database entries."
            ),
            color=discord.Color.blue(),
            timestamp=datetime.now(),
        )

        # 1. Summary Stats
        embed.add_field(name="RSI Members", value=str(len(rsi_handles)), inline=True)
        embed.add_field(name="Verified Linked", value=str(len(verified_handles)), inline=True)
        embed.add_field(name="Not Verified", value=str(len(missing_from_db)), inline=True)

        # 2. List Missing (Limit for Embed)
        if missing_from_db:
            missing_str = "\n".join([f"- `{h}`" for h in missing_from_db[:30]])
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
