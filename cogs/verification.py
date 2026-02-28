import os
import random
import sqlite3
import string

import aiohttp
import discord
from bs4 import BeautifulSoup
from discord import app_commands
from discord.ext import commands


class VerifyNowView(discord.ui.View):
    def __init__(self, cog, handle: str, code: str):
        super().__init__(timeout=None)
        self.cog = cog
        self.handle = handle
        self.code = code

    @discord.ui.button(label="Verify Now", style=discord.ButtonStyle.success, emoji="✅")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        success, message = await self.cog._scrape_rsi_bio(self.handle, self.code)

        if success:
            # 1. Update database
            self.cog._link_account(interaction.user.id, self.handle)

            # Fetch the actual Member object from the guild (interaction.user is a User, not a Member)
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

                # 3. Add Verified Role
                role_id_str = self.cog._get_config("verified_role_id")
                if role_id_str:
                    verified_role = interaction.guild.get_role(int(role_id_str))
                    if verified_role:
                        try:
                            await member.add_roles(verified_role)
                        except discord.Forbidden:
                            print(
                                f"[Verify] Forbidden: Could not assign role '{verified_role.name}' "
                                f"to {member}"
                            )
                    else:
                        print(f"[Verify] Warning: Configured role ID '{role_id_str}' not found in guild.")

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


class RSIVerification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "data/enforcer.db"
        self._setup_db()

    def _setup_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rsi_links (
                    discord_id INTEGER PRIMARY KEY,
                    rsi_handle TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rsi_config (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
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

    def _get_config(self, key: str) -> str:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM rsi_config WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else None

    def _is_verified(self, discord_id: int) -> str:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT rsi_handle FROM rsi_links WHERE discord_id = ?", (discord_id,))
            row = cursor.fetchone()
            return row[0] if row else None

    def _link_account(self, discord_id: int, handle: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO rsi_links (discord_id, rsi_handle)
                VALUES (?, ?)
            """,
                (discord_id, handle),
            )
            conn.commit()

    async def _scrape_rsi_bio(self, handle: str, code: str) -> tuple[bool, str]:
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
                    for div in value_divs:
                        text = div.get_text(strip=True)
                        if code in text:
                            return True, "Code successfully validated against the bio!"
                        bio_text += " " + text

                    return False, (
                        "The code was not found in your Short Bio. Sometimes RSI caches profiles—"
                        "wait a minute and try again."
                    )
            except Exception as e:
                return False, f"Scraping error: {str(e)}"

    def _generate_code(self) -> str:
        # e.g., SCANZ-A7K9
        suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"SCANZ-{suffix}"

    @app_commands.command(name="verify", description="Link your Discord account to your RSI Handle.")
    @app_commands.describe(handle="Your exact Star Citizen RSI Handle")
    async def verify(self, interaction: discord.Interaction, handle: str):
        # 1. Check if they are already verified
        existing_handle = self._is_verified(interaction.user.id)
        if existing_handle:
            await interaction.response.send_message(
                f"You are already verified and linked to the RSI Handle **{existing_handle}**.",
                ephemeral=True,
            )
            return

        # 2. Generate a challenge code
        code = self._generate_code()

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

        view = VerifyNowView(self, handle, code)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(
        name="set_verified_role", description="Admin: Set the role granted upon successful RSI Verification."
    )
    @app_commands.describe(role="The role to grant verified users.")
    @app_commands.default_permissions(administrator=True)
    async def set_verified_role(self, interaction: discord.Interaction, role: discord.Role):
        self._set_config("verified_role_id", str(role.id))
        await interaction.response.send_message(
            f"✅ Verified role successfully set to {role.mention}.", ephemeral=True
        )

    @app_commands.command(
        name="grant_verified",
        description="Admin: Manually grant the verified role and RSI nickname to a member.",
    )
    @app_commands.describe(member="The Discord member to grant the verified role to.")
    @app_commands.default_permissions(administrator=True)
    async def grant_verified(self, interaction: discord.Interaction, member: discord.Member):
        rsi_handle = self._is_verified(member.id)
        if not rsi_handle:
            await interaction.response.send_message(
                f"❌ **{member.mention}** is not verified in the database. "
                "They must complete `/verify` first.",
                ephemeral=True,
            )
            return

        messages = []

        # Apply nickname (DISABLED - Permission Issues)
        # try:
        #     await member.edit(nick=rsi_handle)
        #     messages.append(f"✅ Nickname set to `{rsi_handle}`.")
        # except discord.Forbidden:
        #     messages.append("⚠️ Could not set nickname (permission denied).")

        # Apply role
        role_id_str = self._get_config("verified_role_id")
        if role_id_str:
            verified_role = interaction.guild.get_role(int(role_id_str))
            if verified_role:
                try:
                    await member.add_roles(verified_role)
                    messages.append(f"✅ Granted role {verified_role.mention}.")
                except discord.Forbidden:
                    messages.append(f"⚠️ Could not assign role `{verified_role.name}` (permission denied).")
            else:
                messages.append("⚠️ Configured role not found in server — re-run `/set_verified_role`.")
        else:
            messages.append("⚠️ No verified role configured. Run `/set_verified_role` first.")

        await interaction.response.send_message(
            f"**Grant Verified: {member.display_name}** (`{rsi_handle}`)\n" + "\n".join(messages),
            ephemeral=True,
        )

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        pass  # Nickname Enforcement Disabled - (Permission Issues)

        # # Only process if the nickname actually changed
        # if before.nick == after.nick:
        #     return
        #
        # # Check if the user is verified
        # rsi_handle = self._is_verified(after.id)
        # if not rsi_handle:
        #     return
        #
        # # If they cleared their nickname, 'after.nick' is None. We want to force it to their handle.
        # # If they changed it to something else, force it back.
        # if after.nick != rsi_handle:
        #     try:
        #         await after.edit(nick=rsi_handle)
        #     except discord.Forbidden:
        #         pass


async def setup(bot):
    await bot.add_cog(RSIVerification(bot))
