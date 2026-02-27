import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import os

class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "data/reaction_roles.db"
        self.reaction_roles = {} 
        self._setup_db()
        self._load_from_db()

    def _setup_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reaction_roles (
                    message_id INTEGER,
                    emoji TEXT,
                    role_id INTEGER,
                    PRIMARY KEY (message_id, emoji)
                )
            ''')
            conn.commit()

    def _load_from_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT message_id, emoji, role_id FROM reaction_roles')
            for row in cursor.fetchall():
                msg_id, emoji, role_id = row
                if msg_id not in self.reaction_roles:
                    self.reaction_roles[msg_id] = {}
                self.reaction_roles[msg_id][emoji] = role_id

    @app_commands.command(name="setup_reaction_role", description="Setup a reaction role message")
    @app_commands.describe(role="The role to assign", emoji="The emoji to react with", message="Message content")
    async def setup_reaction_role(self, interaction: discord.Interaction, role: discord.Role, emoji: str, message: str):
        embed = discord.Embed(title="Reaction Roles", description=message, color=discord.Color.green())
        embed.add_field(name="Role", value=f"{emoji} : {role.mention}", inline=False)
        
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        await msg.add_reaction(emoji)
        
        # Store the mapping in memory
        if msg.id not in self.reaction_roles:
            self.reaction_roles[msg.id] = {}
        self.reaction_roles[msg.id][emoji] = role.id
        
        # Store the mapping in the database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO reaction_roles (message_id, emoji, role_id)
                VALUES (?, ?, ?)
            ''', (msg.id, emoji, role.id))
            conn.commit()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.message_id in self.reaction_roles:
            emoji = str(payload.emoji)
            if emoji in self.reaction_roles[payload.message_id]:
                guild = self.bot.get_guild(payload.guild_id)
                role_id = self.reaction_roles[payload.message_id][emoji]
                role = guild.get_role(role_id)
                if role:
                    member = guild.get_member(payload.user_id)
                    if member and not member.bot:
                        await member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.message_id in self.reaction_roles:
            emoji = str(payload.emoji)
            if emoji in self.reaction_roles[payload.message_id]:
                guild = self.bot.get_guild(payload.guild_id)
                role_id = self.reaction_roles[payload.message_id][emoji]
                role = guild.get_role(role_id)
                if role:
                    member = guild.get_member(payload.user_id)
                    if member and not member.bot:
                        await member.remove_roles(role)

async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))
