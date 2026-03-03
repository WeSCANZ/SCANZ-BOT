import asyncio
import json
import os
import sqlite3
import typing

import discord
from discord import app_commands
from discord.ext import commands


def load_config():
    config_path = os.path.join("config", "enforcer_template.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    print(f"Warning: load_config could not find {config_path}")
    return {}


CONFIG = load_config()

POST_TYPE_CHOICES = (
    [app_commands.Choice(name=v.get("name", k), value=k) for k, v in CONFIG.get("post_types", {}).items()][
        :25
    ]
    if CONFIG.get("post_types")
    else [
        app_commands.Choice(name="Event", value="Event"),
        app_commands.Choice(name="Ping", value="Ping"),
        app_commands.Choice(name="Announcement", value="Announcement"),
    ]
)

PING_ROLE_CHOICES = (
    [app_commands.Choice(name=v.get("name", k), value=k) for k, v in CONFIG.get("ping_roles", {}).items()][
        :25
    ]
    if CONFIG.get("ping_roles")
    else []
)


GAME_LOOP_CHOICES = (
    [app_commands.Choice(name=v, value=v) for v in CONFIG.get("game_loops", [])][:25]
    if CONFIG.get("game_loops")
    else [app_commands.Choice(name="General", value="General")]
)


class PingSubscriptionButton(discord.ui.Button):
    def __init__(self, key: str, label: str, role_id: int):
        super().__init__(
            style=discord.ButtonStyle.secondary, label=f"🔔 {label}", custom_id=f"ping_sub_{key}"
        )
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
            return

        role = interaction.guild.get_role(self.role_id)
        if not role:
            await interaction.response.send_message(
                "❌ This ping role is no longer configured correctly (Role ID not found).",
                ephemeral=True,
            )
            return

        user = typing.cast(discord.Member, interaction.user)
        if role in user.roles:
            await user.remove_roles(role)
            await interaction.response.send_message(f"✅ Unsubscribed from **{role.name}**.", ephemeral=True)
        else:
            await user.add_roles(role)
            await interaction.response.send_message(f"✅ Subscribed to **{role.name}**.", ephemeral=True)


class PingSubscriptionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Persistent view

        # Add buttons based on CONFIG
        ping_roles = CONFIG.get("ping_roles", {})
        for key, value in ping_roles.items():
            role_id = value.get("role_id")
            if role_id and role_id != 0:
                label = value.get("name", key)
                # Cap label length for button
                if len(label) > 75:
                    label = label[:72] + "..."
                self.add_item(PingSubscriptionButton(key, label, role_id))


class FormatSetupView(discord.ui.View):
    def __init__(self, cog: "MessageEnforcer", channel: discord.TextChannel):
        super().__init__(timeout=300)
        self.cog = cog
        self.channel = channel

        max_loops = min(25, len(GAME_LOOP_CHOICES))
        self.loop_select = discord.ui.Select(
            placeholder="Choose Allowed Game Loops",
            min_values=1,
            max_values=max_loops,
            options=[discord.SelectOption(label=c.name, value=c.value) for c in GAME_LOOP_CHOICES[:25]],
        )
        self.loop_select.callback = self.loop_callback
        self.add_item(self.loop_select)

        self.selected_loops = []

    async def loop_callback(self, interaction: discord.Interaction):
        self.selected_loops = self.loop_select.values
        await interaction.response.defer()

    @discord.ui.button(label="Save Configuration & Post Info", style=discord.ButtonStyle.success, row=2)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_loops:
            await interaction.response.send_message("Please select at least one Game Loop.", ephemeral=True)
            return

        self.cog._set_channel_config(self.channel.id, ["Ping"], self.selected_loops)

        # Generate informational embed
        embed = discord.Embed(
            title="Channel Formatting Rules",
            description=(
                "This channel has strict formatting rules for pings.\n"
                "Please use the `/ping` command to submit requests."
            ),
            color=discord.Color.blue(),
        )
        embed.add_field(name="Allowed Game Loops", value=", ".join(self.selected_loops), inline=False)
        embed.set_footer(text="Use /ping to create your entry!")

        await self.channel.send(embed=embed)
        await interaction.response.send_message(
            f"Configuration saved and info embed posted in {self.channel.mention}.", ephemeral=True
        )
        self.stop()


class MessageEnforcer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_path = "data/enforcer.db"
        self._setup_db()
        # Register the persistent view
        self.bot.add_view(PingSubscriptionView())

    def _setup_db(self):
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        # Create table if it doesn't exist
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS enforced_channels (
                    channel_id INTEGER PRIMARY KEY
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS channel_configs (
                    channel_id INTEGER PRIMARY KEY,
                    allowed_types TEXT,
                    allowed_loops TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS post_targets (
                    post_type TEXT PRIMARY KEY,
                    channel_id INTEGER NOT NULL
                )
            """)
            conn.commit()

    def _set_channel_config(self, channel_id: int, types: list, loops: list):
        types_str = json.dumps(types)
        loops_str = json.dumps(loops)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO channel_configs (channel_id, allowed_types, allowed_loops) 
                VALUES (?, ?, ?)
                ON CONFLICT(channel_id) DO UPDATE SET 
                    allowed_types=excluded.allowed_types, 
                    allowed_loops=excluded.allowed_loops
            """,
                (channel_id, types_str, loops_str),
            )
            conn.commit()

    def _get_channel_config(self, channel_id: int):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT allowed_types, allowed_loops FROM channel_configs WHERE channel_id = ?", (channel_id,)
            )
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row[0]), json.loads(row[1])
                except Exception:
                    pass
            return None, None

    def _set_post_target(self, post_type: str, channel_id: int):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO post_targets (post_type, channel_id) 
                VALUES (?, ?)
                ON CONFLICT(post_type) DO UPDATE SET 
                    channel_id=excluded.channel_id
            """,
                (post_type, channel_id),
            )
            conn.commit()

    def _get_post_target(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT channel_id FROM post_targets WHERE post_type = "Ping"')
            row = cursor.fetchone()
            return row[0] if row else None

    async def _resolve_target_channel(
        self, interaction: discord.Interaction, explicit_channel: discord.TextChannel = None
    ) -> discord.TextChannel:
        if explicit_channel:
            return explicit_channel

        target_id = self._get_post_target()
        if target_id:
            channel = interaction.guild.get_channel(target_id)
            if channel:
                return channel

        return interaction.channel

    def _is_enforced(self, channel_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM enforced_channels WHERE channel_id = ?", (channel_id,))
            return cursor.fetchone() is not None

    def _set_enforced(self, channel_id: int, enforced: bool):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if enforced:
                cursor.execute(
                    "INSERT OR IGNORE INTO enforced_channels (channel_id) VALUES (?)", (channel_id,)
                )
            else:
                cursor.execute("DELETE FROM enforced_channels WHERE channel_id = ?", (channel_id,))
            conn.commit()

    @app_commands.command(
        name="enforce_channel",
        description="Admin: Toggle strict message enforcement for the current channel.",
    )
    @app_commands.default_permissions(administrator=True)
    async def enforce_channel(self, interaction: discord.Interaction, enabled: bool):
        """Toggle strict message enforcement for the current channel."""
        self._set_enforced(interaction.channel_id, enabled)

        status = "enabled" if enabled else "disabled"
        await interaction.response.send_message(
            f"Message enforcement has been {status} for this channel.", ephemeral=True
        )

    @app_commands.command(
        name="scanz_format", description="Admin: Interactive setup for the channel's enforced log format."
    )
    @app_commands.default_permissions(administrator=True)
    async def scanz_format(self, interaction: discord.Interaction):
        """Interactive command to start formatting a channel."""
        if not self._is_enforced(interaction.channel_id):
            await interaction.response.send_message(
                "This channel is not enforced. First enable it using: `/enforce_channel enabled:True`.",
                ephemeral=True,
            )
            return

        view = FormatSetupView(self, interaction.channel)
        await interaction.response.send_message(
            "Please configure the allowed formats for this channel below:", view=view, ephemeral=True
        )

    @app_commands.command(
        name="set_ping_target", description="Admin: Set a default target channel for pings."
    )
    @app_commands.default_permissions(administrator=True)
    async def set_ping_target(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set a default target channel for pings."""
        self._set_post_target("Ping", channel.id)
        await interaction.response.send_message(
            f"Successfully set the default channel for pings to {channel.mention}.", ephemeral=True
        )

    @app_commands.command(
        name="scanz_subscriptions",
        description="Admin: Post the role subscription message in the current channel.",
    )
    @app_commands.default_permissions(administrator=True)
    async def scanz_subscriptions(self, interaction: discord.Interaction):
        """Post the role subscription message."""
        embed = discord.Embed(
            title=CONFIG.get("messages", {}).get("subscription_title", "Ping Role Subscriptions"),
            description=CONFIG.get("messages", {}).get(
                "subscription_description", "Subscribe to pings here."
            ),
            color=discord.Color.gold(),
        )
        embed.set_footer(text=CONFIG.get("embeds", {}).get("footer_text", "SCANZ Message Enforcer"))

        view = PingSubscriptionView()
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("Subscription message posted.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bot messages and webhooks
        if message.author.bot or message.webhook_id:
            return

        # Check if the channel is enforced
        if not self._is_enforced(message.channel.id):
            return

        # Bypass enforcement for specific roles
        if isinstance(message.author, discord.Member):
            allowed_roles = {"officer", "officers", "custodian", "custodians"}
            user_roles = {role.name.lower() for role in message.author.roles}
            if allowed_roles & user_roles:
                return

        # Check if it might be a valid command from an old prefix (we want to encourage slash commands,
        # but discord handles slash without hitting on_message with content in the same way usually.
        # Regular messages hit this though.)
        # If we really want ZERO non-bot messages, we just delete everything.
        # The slash command responses come from the bot.

        try:
            # Delete the user's message
            await message.delete()

            # Inform the user via DM
            warning_template = CONFIG.get("messages", {}).get(
                "warning_text",
                (
                    "Your message in {channel} was deleted because the channel is strictly formatted.\n"
                    "Please use the `/ping` command to submit requests in that channel."
                ),
            )
            warning_text = warning_template.replace("{channel}", message.channel.mention)
            try:
                await message.author.send(warning_text)
            except discord.Forbidden:
                # Can't DM user, optionally send a temporary message in the channel
                await message.channel.send(f"{message.author.mention}, {warning_text}", delete_after=10)
        except discord.errors.NotFound:
            # Message already deleted
            pass
        except discord.errors.Forbidden:
            # Bot lacks permissions to delete messages
            print(f"Warning: Missing permissions to delete message in {message.channel.name}")

    @app_commands.command(name="ping", description="Create a formatted alert/ping.")
    @app_commands.choices(game_loop=GAME_LOOP_CHOICES)
    async def ping_command(
        self,
        interaction: discord.Interaction,
        game_loop: app_commands.Choice[str],
        description: str,
        time: str = None,
        location: str = None,
        requirements: str = None,
        link: str = None,
        channel: discord.TextChannel = None,
    ):
        """Create a formatted alert/ping post."""

        # Check if there are constraints for this channel
        allowed_types, allowed_loops = self._get_channel_config(interaction.channel_id)

        if allowed_loops is not None and game_loop.value not in allowed_loops:
            await interaction.response.send_message(
                f"The game loop **{game_loop.value}** is not allowed in this channel.\n"
                f"Allowed loops: {', '.join(allowed_loops)}",
                ephemeral=True,
            )
            return

        color = discord.Color.blue()  # Default color

        embed = discord.Embed(title=f"**Ping** | {game_loop.value}", description=description, color=color)

        if time:
            embed.add_field(name="Time", value=time, inline=True)
        if location:
            embed.add_field(name="Location", value=location, inline=True)
        if requirements:
            embed.add_field(name="Requirements", value=requirements, inline=False)
        if link:
            link_val = f"[Click Here]({link})" if link.startswith("http") else link
            embed.add_field(name="Link to Event/Voice", value=link_val, inline=False)

        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else None,
        )

        # Resolve the target channel
        target_channel = await self._resolve_target_channel(interaction, channel)

        # Ping logic - retrieve configured role or fall back to name
        def _get_scanz_role():
            role_id = None
            cog = self.bot.get_cog("RSIVerification")
            if cog:
                role_id = cog._get_config("scanz_role_id")
            if role_id:
                return interaction.guild.get_role(int(role_id))
            # fallback to name
            return discord.utils.get(interaction.guild.roles, name="SCANZ")

        scanz_role = _get_scanz_role()
        mention_str = ""

        if scanz_role:
            mention_str = scanz_role.mention

            # Track original mentionability so we only reset if WE changed it
            was_mentionable = scanz_role.mentionable
            if not was_mentionable:
                try:
                    await scanz_role.edit(
                        mentionable=True, reason=f"Pinging {scanz_role.name} role via /ping command"
                    )
                except discord.Forbidden:
                    pass  # Bot lacks permission to edit role
        else:
            await interaction.response.send_message(
                "❌ Error: Could not find the SCANZ role in this server. Please contact an admin.",
                ephemeral=True,
            )
            return

        # Send the embed to the target channel
        try:
            await target_channel.send(content=mention_str, embed=embed)

            # Only reset mentionability if we were the one who enabled it
            if scanz_role and not was_mentionable:
                await asyncio.sleep(1)
                try:
                    await scanz_role.edit(mentionable=False, reason="Resetting @SCANZ mentionability")
                except discord.Forbidden:
                    pass

            # Always send an ephemeral confirmation — never re-post the embed via interaction
            if target_channel.id == interaction.channel_id:
                await interaction.response.send_message(
                    "✅ Your ping has been posted in this channel.", ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"✅ Your post has been successfully published in {target_channel.mention}",
                    ephemeral=True,
                )
        except discord.errors.Forbidden:
            await interaction.response.send_message(
                f"❌ Error: I do not have permission to send messages in {target_channel.mention}.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(MessageEnforcer(bot))
