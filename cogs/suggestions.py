import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import os
from datetime import datetime

class Suggestions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_path = "data/suggestions.db"
        self._setup_db()

    def _setup_db(self):
        """Initialize the database and tables."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Configuration table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS suggestion_config (
                    guild_id INTEGER PRIMARY KEY,
                    channel_id INTEGER NOT NULL
                )
            ''')
            # Suggestions log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS suggestions_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    suggestion_text TEXT NOT NULL,
                    anonymous INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    thread_id INTEGER
                )
            ''')
            
            # Migration: Ensure thread_id column exists if table was already created
            try:
                cursor.execute('ALTER TABLE suggestions_log ADD COLUMN thread_id INTEGER')
            except sqlite3.OperationalError:
                pass # Already exists
            
            conn.commit()

    def _set_config(self, guild_id: int, channel_id: int):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO suggestion_config (guild_id, channel_id) 
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET 
                    channel_id=excluded.channel_id
            ''', (guild_id, channel_id))
            conn.commit()

    def _get_config(self, guild_id: int) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT channel_id FROM suggestion_config WHERE guild_id = ?', (guild_id,))
            row = cursor.fetchone()
            return row[0] if row else None

    def _log_suggestion(self, user_id: int, text: str, anonymous: bool, thread_id: int = None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO suggestions_log (user_id, suggestion_text, anonymous, timestamp, thread_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, text, 1 if anonymous else 0, datetime.now().isoformat(), thread_id))
            conn.commit()

    @app_commands.command(name="set_suggestion_channel", description="Admin: Set the channel where suggestions will be sent.")
    @app_commands.default_permissions(administrator=True)
    async def set_suggestion_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set the target channel for suggestions."""
        self._set_config(interaction.guild_id, channel.id)
        await interaction.response.send_message(f"✅ Suggestion channel set to {channel.mention}.", ephemeral=True)

    @app_commands.command(name="suggestion", description="Submit a suggestion to the SCANZ team.")
    @app_commands.describe(text="Your suggestion or feedback", anonymous="Whether to hide your name from the staff")
    async def suggestion(self, interaction: discord.Interaction, text: str, anonymous: bool = False):
        """Submit a suggestion."""
        target_channel_id = self._get_config(interaction.guild_id)
        
        if not target_channel_id:
            await interaction.response.send_message("❌ Suggestions are not currently enabled for this server (no target channel set).", ephemeral=True)
            return

        target_channel = interaction.guild.get_channel(target_channel_id)
        if not target_channel:
            await interaction.response.send_message("❌ Suggestion channel not found. Please ask an admin to reconfigure it.", ephemeral=True)
            return

        # Log to database
        self._log_suggestion(interaction.user.id, text, anonymous)

        # Create Embed
        embed = discord.Embed(
            title="New Suggestion",
            description=text,
            color=discord.Color.gold() if not anonymous else discord.Color.light_grey(),
            timestamp=datetime.now()
        )

        if anonymous:
            embed.set_author(name="Anonymous Member", icon_url="https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y")
            footer_text = "Anonymous Suggestion"
        else:
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else None)
            footer_text = f"Submitted by {interaction.user.name} ({interaction.user.id})"
        
        embed.set_footer(text=footer_text)

        try:
            msg = await target_channel.send(embed=embed)
            
            # Create a discussion thread
            thread = await msg.create_thread(
                name=f"Discussion: {text[:50]}{'...' if len(text) > 50 else ''}",
                auto_archive_duration=10080 # 7 days
            )
            
            # Log to database with thread ID
            self._log_suggestion(interaction.user.id, text, anonymous, thread.id)
            
            await interaction.response.send_message("✅ Your suggestion has been submitted successfully! A discussion thread has been created.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to send messages or create threads in the suggestion channel.", ephemeral=True)

    def _find_author_by_thread(self, thread_id: int) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM suggestions_log WHERE thread_id = ?', (thread_id,))
            row = cursor.fetchone()
            return row[0] if row else None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bot messages
        if message.author.bot:
            return

        # Check if the message is in a thread
        if not isinstance(message.channel, discord.Thread):
            return

        # Check if the thread belongs to a suggestion
        author_id = self._find_author_by_thread(message.channel.id)
        if not author_id:
            return

        # Don't notify the author of their own replies
        if message.author.id == author_id:
            return

        # Notify the original author
        try:
            author = await self.bot.fetch_user(author_id)
            if author:
                embed = discord.Embed(
                    title="New Reply to Your Suggestion",
                    description=f"Someone has replied to the discussion thread for your suggestion in **{message.guild.name}**.",
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )
                embed.add_field(name="Reply Content", value=message.content[:1024] or "*[Embed/Image]*", inline=False)
                embed.add_field(name="Link", value=f"[Click here to view the reply]({message.jump_url})", inline=False)
                
                await author.send(embed=embed)
        except discord.Forbidden:
            # Author has DMs disabled
            pass
        except Exception as e:
            print(f"Error sending suggestion notification: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Suggestions(bot))
