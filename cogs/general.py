import datetime
import random

import discord
import pytz
from discord import app_commands
from discord.ext import commands


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="hi", help="Says hello with a random verbose message.")
    async def hi(self, ctx):
        responses = [
            "Greetings, starfarer! I hope your travels through the verse have been profitable and safe.",
            "Hello there! I am the SCANZ Bot, at your service. How may I assist you today?",
            "Top of the morning to you! Or evening, depending on which planet you're orbiting.",
        ]
        await ctx.send(random.choice(responses))

    @commands.command(name="time", help="Displays current time across SCANZ timezones.")
    async def time(self, ctx):
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

        await ctx.send(embed=embed)

    @app_commands.command(name="scanz_commands", description="Lists all available SCANZ-BOT commands.")
    async def scanz_commands(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="SCANZ-BOT Command Guide",
            description="Here is a list of all available commands:",
            color=discord.Color.gold(),
        )

        # General/Utility
        embed.add_field(name="`!hi`", value="Says hello with a random message.", inline=False)
        embed.add_field(name="`!ping`", value="Checks if the bot is responsive.", inline=False)
        embed.add_field(name="`!time`", value="Displays current time across SCANZ timezones.", inline=False)
        embed.add_field(
            name="`!sync`", value="Admin: Force instant slash command update for this server.", inline=False
        )
        embed.add_field(name="`/scanz_commands`", value="Lists all available commands.", inline=False)

        # SC Tools
        embed.add_field(name="`!status`", value="Fetches current Star Citizen server status.", inline=False)
        embed.add_field(
            name="`!wiki [term]`", value="Generates a search link for the Star Citizen Wiki.", inline=False
        )
        embed.add_field(name="`!org`", value="Displays information and links for SCANZ.", inline=False)
        embed.add_field(
            name="`/verify`", value="Link your Discord to your RSI Handle using a bio checksum.", inline=False
        )

        # Staff/Admin (staff role or Administrator; set with /set_staff_role)
        embed.add_field(
            name="`/set_staff_role`",
            value="Admin only: Set the role that can use staff commands (e.g. Custodian).",
            inline=False,
        )
        embed.add_field(
            name="`/clear_staff_role`",
            value="Admin only: Clear staff role so only Administrator can use staff commands.",
            inline=False,
        )
        embed.add_field(
            name="`/setup_reaction_role`", value="Manage Roles: Create a reaction role message.", inline=False
        )
        embed.add_field(
            name="`/enforce_channel`", value="Staff: Toggle strict message enforcement.", inline=False
        )
        embed.add_field(
            name="`/scanz_format`",
            value="Staff: Setup allowed Post Types/Game Loops for a channel.",
            inline=False,
        )
        embed.add_field(
            name="`/set_ping_target`",
            value="Staff: Map a channel to a specific category for `/ping`.",
            inline=False,
        )
        embed.add_field(
            name="`/scanz_subscriptions`",
            value="Staff: Post a persistent message to subscribe to ping roles.",
            inline=False,
        )
        embed.add_field(
            name="`/set_verified_role`",
            value="Staff: Configure the role given to verified members.",
            inline=False,
        )
        embed.add_field(
            name="`/grant_verified`",
            value="Staff: Manually apply roles/nick to a verified user.",
            inline=False,
        )
        embed.add_field(
            name="`/manual_verify`", value="Staff: Manually link a member to an RSI handle.", inline=False
        )
        embed.add_field(
            name="`/export_verified`", value="Staff: Export verification database to CSV.", inline=False
        )
        embed.add_field(name="`/search_verified`", value="Staff: Search for a verified member.", inline=False)
        embed.add_field(
            name="`/org_full_sync`", value="Staff: Sync RSI roster with bot database.", inline=False
        )
        embed.add_field(
            name="`/set_suggestion_channel`", value="Staff: Set channel where suggestions are sent.", inline=False
        )
        embed.add_field(
            name="`/set_roster_channel`", value="Staff: Set channel for roster audit notifications.", inline=False
        )
        embed.add_field(
            name="`/roster_audit`", value="Staff: Manually check verified members' Org status.", inline=False
        )

        # Enforcer Post
        embed.add_field(
            name="`/ping`",
            value=(
                "Create a formatted Event/Ping/Announcement post (mentions @SCANZ). "
                "Used in enforced/targeted channels."
            ),
            inline=False,
        )

        embed.set_footer(text="To see full argument details, type the command or check our docs.")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(General(bot))
