import os
import subprocess

import discord
from discord import app_commands
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
        cogs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cogs")

        # Load verification cog first to ensure database schema is created
        if os.path.exists(os.path.join(cogs_dir, "verification.py")):
            try:
                await self.load_extension("cogs.verification")
            except commands.ExtensionError as e:
                print(f"Failed to load verification cog: {e}")

        for filename in os.listdir(cogs_dir):
            if filename.endswith(".py") and filename != "verification.py":
                try:
                    await self.load_extension(f"cogs.{filename[:-3]}")
                except commands.ExtensionError as e:
                    print(f"Failed to load cog {filename}: {e}")

        # Sync slash commands
        await self.tree.sync()
        print(f"Synced command tree for {self.user}")

    async def on_ready(self):
        if not self.user:
            return

        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")

        # Get the channel from .env
        channel_id_str = os.getenv("LOG_CHANNEL_ID")
        if channel_id_str:
            try:
                channel_id = int(channel_id_str)
                channel = self.get_channel(channel_id)

                if isinstance(channel, discord.TextChannel):
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


@bot.tree.error
async def on_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Send a user-friendly message when a permission check fails."""
    if isinstance(error, app_commands.CheckFailure):
        try:
            if interaction.response.is_done():
                await interaction.followup.send(
                    "You don't have permission to use this command.", ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "You don't have permission to use this command.", ephemeral=True
                )
        except discord.NotFound:
            pass
        return
    raise error


@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")


if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in environment variables.")
    else:
        bot.run(TOKEN)
