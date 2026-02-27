import discord
from discord.ext import commands
import os

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.welcome_channel_id = int(os.getenv('WELCOME_CHANNEL_ID', 0))

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if self.welcome_channel_id:
            channel = self.bot.get_channel(self.welcome_channel_id)
            if channel:
                embed = discord.Embed(
                    title=f"Welcome to SCANZ, {member.name}!",
                    description=f"We are glad to have you here, {member.mention}. Please check out the rules and verify yourself to get access to the rest of the server.",
                    color=discord.Color.blue()
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                await channel.send(embed=embed)
            else:
                print(f"Welcome channel with ID {self.welcome_channel_id} not found.")

async def setup(bot):
    await bot.add_cog(Welcome(bot))
