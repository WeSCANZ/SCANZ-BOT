import datetime
import os
import random
from pathlib import Path

import discord
import dotenv
import pytz
from discord import app_commands
from discord.ext import commands


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="latency", description="Checks the bot's global latency.")
    async def latency(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"**WebSocket Latency:** `{latency}ms`",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="hi", description="Says hello with a random, personalized message.")
    async def hi(self, interaction: discord.Interaction):
        user_name = interaction.user.display_name
        responses = [
            f"Greetings, {user_name}! I hope your travels through the verse have been profitable and safe.",
            f"Hello there, {user_name}! I am the SCANZ Bot, at your service. How may I assist you today?",
            f"Top of the morning to you, {user_name}! Or evening, depending on which planet you're orbiting.",
            f"o7 {user_name}! Ready for deployment?",
            f"Aha! {user_name} approaches. The scanners didn't pick you up until just now!",
        ]
        await interaction.response.send_message(random.choice(responses))

    @app_commands.command(name="time", description="Displays current time across SCANZ timezones.")
    async def time(self, interaction: discord.Interaction):
        zones = {
            "Indochina (ICT)": "Asia/Bangkok",
            "Perth (AWST)": "Australia/Perth",
            "Melbourne/Sydney (AET)": "Australia/Sydney",
            "New Zealand (NZT)": "Pacific/Auckland",
        }

        embed = discord.Embed(title="SCANZ Global Times", color=discord.Color.blurple())

        now_utc = datetime.datetime.now(datetime.timezone.utc)

        for name, tz_str in zones.items():
            tz = pytz.timezone(tz_str)
            local_time = now_utc.astimezone(tz)
            embed.add_field(name=name, value=local_time.strftime("**%I:%M %p**\n%a, %b %d"), inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="scanz_commands", description="Lists all available SCANZ-BOT commands.")
    async def scanz_commands(self, interaction: discord.Interaction):
        # Discord enforces a max of 25 fields per embed — split across two embeds.

        # ----- Embed 1: Everyone Commands (8 fields) -----
        embed1 = discord.Embed(
            title="SCANZ-BOT Command Guide",
            description="**All Members**",
            color=discord.Color.gold(),
        )
        embed1.add_field(name="`/hi`", value="Says hello with a personalized message.", inline=False)
        embed1.add_field(name="`/latency`", value="Checks the bot's WebSocket latency.", inline=False)
        embed1.add_field(name="`/time`", value="Displays current time across SCANZ timezones.", inline=False)
        embed1.add_field(name="`/scanz_commands`", value="Lists all available commands.", inline=False)
        embed1.add_field(name="`/suggestion`", value="Submit a suggestion to the SCANZ team.", inline=False)
        embed1.add_field(
            name="`/verify`", value="Link your Discord to your RSI Handle using a bio checksum.", inline=False
        )
        embed1.add_field(name="`/list_orgs`", value="Displays configured organisations.", inline=False)
        embed1.add_field(
            name="`/ping`",
            value="Create a formatted alert/ping post (mentions @SCANZ).",
            inline=False,
        )

        # ----- Embed 2: Staff & Admin Commands (23 fields) -----
        embed2 = discord.Embed(
            description="**Staff** *(Requires Staff Role or Administrator)*",
            color=discord.Color.orange(),
        )
        embed2.add_field(name="`/enforce_channel`", value="Toggle strict message enforcement.", inline=False)
        embed2.add_field(
            name="`/scanz_format`", value="Setup allowed Game Loops for a channel.", inline=False
        )
        embed2.add_field(
            name="`/set_ping_target`", value="Set the default channel for `/ping`.", inline=False
        )
        embed2.add_field(
            name="`/scanz_subscriptions`", value="Post the ping role subscription message.", inline=False
        )
        embed2.add_field(name="`/set_suggestion_channel`", value="Set channel for suggestions.", inline=False)
        embed2.add_field(name="`/setup_reaction_role`", value="Create a reaction role message.", inline=False)
        embed2.add_field(name="`/set_main_role`", value="Configure the Main Org member role.", inline=False)
        embed2.add_field(
            name="`/set_affiliate_role`", value="Configure the Affiliate member role.", inline=False
        )
        embed2.add_field(name="`/set_guest_role`", value="Configure the Honored Guest role.", inline=False)
        embed2.add_field(
            name="`/set_unverified_role`", value="Configure the Needs Verification role.", inline=False
        )
        embed2.add_field(name="`/set_scanz_role`", value="Configure the SCANZ identifier role.", inline=False)
        embed2.add_field(name="`/add_org` / `/remove_org`", value="Manage RSI org symbols.", inline=False)
        embed2.add_field(
            name="`/grant_verified`", value="Manually apply verified role to a member.", inline=False
        )
        embed2.add_field(
            name="`/manual_verify`", value="Manually link a member to an RSI handle.", inline=False
        )
        embed2.add_field(name="`/search_verified`", value="Search for a verified member.", inline=False)
        embed2.add_field(
            name="`/export_verified`", value="Export verification database to CSV.", inline=False
        )
        embed2.add_field(name="`/export_unverified`", value="Export unverified members to CSV.", inline=False)
        embed2.add_field(
            name="`/set_roster_channel`", value="Set channel for roster audit reports.", inline=False
        )
        embed2.add_field(
            name="`/roster_audit`", value="Trigger a check of all verified members.", inline=False
        )
        embed2.add_field(
            name="`/org_full_sync`", value="Sync RSI org roster with the bot database.", inline=False
        )

        is_admin = (
            isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator
        )
        if is_admin:
            embed2.add_field(name="— ADMIN ONLY —", value="*Requires Administrator permission*", inline=False)
            embed2.add_field(
                name="`/set_staff_role`", value="Set the role that can use staff commands.", inline=False
            )
            embed2.add_field(
                name="`/set_log_channel`", value="Set the channel for bot boot/update logs.", inline=False
            )
            embed2.add_field(
                name="`/clear_staff_role`", value="Clear the staff role (Admin only).", inline=False
            )

        embed2.set_footer(text="For full argument details, type the command or check COMMANDS.md.")

        await interaction.response.send_message(embeds=[embed1, embed2], ephemeral=True)

    @app_commands.command(
        name="set_log_channel", description="Admin only: Set the channel for bot startup and update logs."
    )
    @app_commands.describe(channel="The channel to send bot startup/update logs to.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(
        lambda i: i.user and isinstance(i.user, discord.Member) and i.user.guild_permissions.administrator
    )
    async def set_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set the log channel. Only users with Administrator can run this."""
        env_path = Path(".env")

        # Check if .env exists, if not create an empty one
        if not env_path.exists():
            env_path.touch()

        dotenv.set_key(env_path, "LOG_CHANNEL_ID", str(channel.id))
        os.environ["LOG_CHANNEL_ID"] = str(channel.id)

        await interaction.response.send_message(
            f"✅ Log channel successfully set to {channel.mention}.", ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(General(bot))
