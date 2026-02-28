import datetime

import aiohttp
import discord
from discord.ext import commands


class StarCitizen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.status_api_url = (
            "https://status.robertsspaceindustries.com/static/content/api/v0/systems.en.json"
        )

    @commands.command(name="status", help="Checks the status of the Star Citizen Persistent Universe.")
    async def status(self, ctx):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(self.status_api_url) as response:
                    if response.status == 200:
                        data = await response.json()

                        embed = discord.Embed(
                            title="RSI Platform Status",
                            url="https://status.robertsspaceindustries.com/",
                            color=discord.Color.orange(),
                            timestamp=datetime.datetime.now(),
                        )

                        for system in data:
                            status_text = system.get("status", "Unknown").capitalize()
                            embed.add_field(
                                name=system.get("name", "Unknown System"),
                                value=f"Status: **{status_text}**",
                                inline=False,
                            )

                        await ctx.send(embed=embed)
                    else:
                        error_embed = discord.Embed(
                            title="RSI Platform Status Error",
                            description=f"Failed to fetch status. HTTP Code: {response.status}",
                            color=discord.Color.red(),
                        )
                        await ctx.send(embed=error_embed)
            except Exception as e:
                error_embed = discord.Embed(
                    title="RSI Platform Status Error",
                    description=f"An error occurred while fetching status: {str(e)}",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=error_embed)

    @commands.command(name="wiki", help="Search the Star Citizen Wiki.")
    async def wiki(self, ctx, *, term: str):
        # Simple search link
        search_url = f"https://starcitizen.tools/Special:Search?query={term.replace(' ', '+')}"

        embed = discord.Embed(
            title=f"Star Citizen Wiki: {term}",
            description=f"[Click here to search for '{term}' on the Wiki]({search_url})",
            color=discord.Color.blue(),
        )
        await ctx.send(embed=embed)

    @commands.command(name="org", help="Displays SCANZ Org information.")
    async def org(self, ctx):
        embed = discord.Embed(
            title="Star Citizen Australia and New Zealand (SCANZ)",
            description="The largest Star Citizen active community in Oceania.",
            color=0x000000,  # Black/Dark
        )
        # Placeholder or real logo if available
        logo_url = "https://robertsspaceindustries.com/media/893950u2677hir/heap_infobox/SCANZ-Logo-2020.png"
        embed.set_thumbnail(url=logo_url)

        embed.add_field(
            name="RSI Org Page",
            value="[SCANZ on RSI](https://robertsspaceindustries.com/orgs/SCANZ)",
            inline=False,
        )
        embed.add_field(name="Discord Invite", value="https://discord.gg/3atj8pjhFH", inline=False)
        embed.add_field(name="Website", value="https://wescanz.com", inline=False)

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(StarCitizen(bot))
