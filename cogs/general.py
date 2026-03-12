import datetime
import random

import discord
import pytz
from discord import app_commands
from discord.ext import commands


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Checks the bot's global latency.")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"**WebSocket Latency:** `{latency}ms`",
            color=discord.Color.green()
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
            f"Aha! {user_name} approaches. The scanners didn't pick you up until just now!"
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
        embed = discord.Embed(
            title="SCANZ-BOT Command Guide",
            description="Here is a list of all available commands:",
            color=discord.Color.gold(),
        )

        # ----- All Users (Everyone) -----
        # General & Utility
        embed.add_field(name="`/hi`", value="Says hello with a personalized message.", inline=False)
        embed.add_field(name="`/ping`", value="Checks the bot's global latency.", inline=False)
        embed.add_field(name="`/time`", value="Displays current time across SCANZ timezones.", inline=False)
        embed.add_field(name="`/scanz_commands`", value="Lists all available commands.", inline=False)
        embed.add_field(name="`/suggestion`", value="Submit a suggestion to the SCANZ team.", inline=False)

        # SC Tools & Org Info
        embed.add_field(name="`/verify`", value="Link your Discord to your RSI Handle using a bio checksum.", inline=False)
        embed.add_field(name="`/list_orgs`", value="Displays configured organisations.", inline=False)
        embed.add_field(name="`/verify`", value="Link your Discord to your RSI Handle using a bio checksum.", inline=False)
        embed.add_field(name="`/list_orgs`", value="Displays configured organisations.", inline=False)

        # Enforcer Post (Ping)
        embed.add_field(
            name="`/ping`",
            value="Create a formatted Event/Announcement post (mentions @SCANZ).",
            inline=False,
        )

        # ----- Admin & Officer Commands (Staff) -----
        embed.add_field(name="--- STAFF COMMANDS ---", value="Requires Staff Role or Administrator", inline=False)
        
        # Enforcement & Channels
        embed.add_field(name="`/enforce_channel`", value="Staff: Toggle strict message enforcement.", inline=False)
        embed.add_field(name="`/scanz_format`", value="Staff: Setup allowed Post Types for a channel.", inline=False)
        embed.add_field(name="`/set_ping_target`", value="Staff: Map a channel to a category for `/ping`.", inline=False)
        embed.add_field(name="`/scanz_subscriptions`", value="Staff: Post a ping role subscription message.", inline=False)
        embed.add_field(name="`/set_suggestion_channel`", value="Staff: Set channel for suggestions.", inline=False)
        embed.add_field(name="`/setup_reaction_role`", value="Manage Roles: Create a reaction role message.", inline=False)

        # Verification Mgmt
        embed.add_field(name="`/set_main_role`", value="Staff: Configure the Main Org member role.", inline=False)
        embed.add_field(name="`/set_affiliate_role`", value="Staff: Configure the Affiliate member role.", inline=False)
        embed.add_field(name="`/set_guest_role`", value="Staff: Configure the Honored Guest role.", inline=False)
        embed.add_field(name="`/set_unverified_role`", value="Staff: Configure role for users needing verification.", inline=False)
        embed.add_field(name="`/set_scanz_role`", value="Staff: Configure an optional filter role for unverified members.", inline=False)
        embed.add_field(name="`/add_org` / `/remove_org`", value="Staff: Manage RSI org symbols.", inline=False)
        embed.add_field(name="`/grant_verified`", value="Staff: Manually apply roles/nick to user.", inline=False)
        embed.add_field(name="`/manual_verify`", value="Staff: Manually link a member to RSI handle.", inline=False)
        embed.add_field(name="`/search_verified`", value="Staff: Search for a verified member.", inline=False)
        embed.add_field(name="`/export_verified`", value="Staff: Export verification database.", inline=False)

        # Roster Monitor
        embed.add_field(name="`/set_roster_channel`", value="Staff: Set channel for roster audits.", inline=False)
        embed.add_field(name="`/roster_audit`", value="Staff: Trigger check of verified members.", inline=False)
        embed.add_field(name="`/org_full_sync`", value="Staff: Sync RSI roster with bot DB.", inline=False)

        # ----- Administrator -----
        embed.add_field(name="--- ADMIN ONLY ---", value="Requires Administrator Permission", inline=False)
        embed.add_field(name="`/set_staff_role`", value="Admin: Set role that can use staff commands.", inline=False)
        embed.add_field(name="`/clear_staff_role`", value="Admin: Clear staff role (only Admin can use).", inline=False)
        embed.add_field(name="`!sync`", value="Admin: Force instant slash command update for this server.", inline=False)

        embed.set_footer(text="To see full argument details, type the command or check COMMANDS.md.")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(General(bot))
