import os
import subprocess

import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
TOKEN = os.getenv("DISCORD_TOKEN")

# Bot Setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True


class ScanzBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Load cogs
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                await self.load_extension(f"cogs.{filename[:-3]}")

        # Sync slash commands
        await self.tree.sync()
        print(f"Synced command tree for {self.user}")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")

        # Get the channel from .env
        channel_id_str = os.getenv("LOG_CHANNEL_ID")
        if channel_id_str:
            try:
                channel_id = int(channel_id_str)
                channel = self.get_channel(channel_id)

                if channel:
                    # Get the latest git commit message and branch
                    try:
                        commit_msg = (
                            subprocess.check_output(
                                ["git", "log", "-1", "--pretty=%B"],
                                stderr=subprocess.DEVNULL,
                            )
                            .decode("utf-8")
                            .strip()
                        )
                        branch = (
                            subprocess.check_output(
                                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                                stderr=subprocess.DEVNULL,
                            )
                            .decode("utf-8")
                            .strip()
                        )
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        commit_msg = "Unknown update"
                        branch = "unknown"

                    await channel.send(
                        f"🚀 **Bot Updated & Online!**\n"
                        f"**Branch:** `{branch}`\n"
                        f"**Latest Change:** `{commit_msg}`"
                    )
            except ValueError:
                print(f"Error: Invalid LOG_CHANNEL_ID format in environment variables: {channel_id_str}")
        else:
            print("Warning: LOG_CHANNEL_ID not found in environment variables.")


bot = ScanzBot()


@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")


if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in environment variables.")
    else:
        bot.run(TOKEN)
