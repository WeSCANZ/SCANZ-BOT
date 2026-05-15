import asyncio
import json
import os
import sqlite3
import typing

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import has_staff_or_admin


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
            f"Configuration saved and info embed posted in {self.channel.mention}.",
            ephemeral=True,
        )

        # Log admin action
        embed = discord.Embed(
            title="Channel Format Setup",
            description=(
                f"**Channel:** {self.channel.mention}\n"
                f"**Allowed Loops:** `{', '.join(self.selected_loops)}`\n"
                f"**Staff:** {interaction.user.mention}"
            ),
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )
        await self.cog.bot.log_admin_action(embed)
        self.stop()


class PingRoleSelectView(discord.ui.View):
    """Ephemeral view shown after /ping to let the user pick which roles to mention."""

    def __init__(self, embed: discord.Embed, target_channel: discord.TextChannel, source_channel_id: int):
        super().__init__(timeout=120)
        self.embed = embed
        self.target_channel = target_channel
        self.source_channel_id = source_channel_id
        self.selected_role_ids: list[int] = []

        # Build select options from ping_roles config; skip unconfigured (role_id == 0) entries
        ping_roles = CONFIG.get("ping_roles", {})
        options = []
        for key, value in ping_roles.items():
            role_id = value.get("role_id", 0)
            if role_id and role_id != 0:
                label = value.get("name", key)
                if len(label) > 100:
                    label = label[:97] + "..."
                options.append(discord.SelectOption(label=label, value=str(role_id)))

        if options:
            self.role_select: discord.ui.Select | None = discord.ui.Select(
                placeholder="Select roles to ping (leave blank for no mention)...",
                min_values=0,
                max_values=len(options),
                options=options,
                row=0,
            )
            self.role_select.callback = self._role_select_callback
            self.add_item(self.role_select)
        else:
            self.role_select = None

    async def _role_select_callback(self, interaction: discord.Interaction):
        if self.role_select is not None:
            self.selected_role_ids = [int(v) for v in self.role_select.values]
        await interaction.response.defer()

    @discord.ui.button(label="Post Ping", style=discord.ButtonStyle.success, emoji="📣", row=1)
    async def post_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        # Resolve roles and temporarily make non-mentionable ones mentionable
        mention_parts: list[str] = []
        roles_to_reset: list[discord.Role] = []

        for role_id in self.selected_role_ids:
            if not interaction.guild:
                continue
            role = interaction.guild.get_role(role_id)
            if not role:
                continue  # Role was deleted or not found — skip silently
            mention_parts.append(role.mention)
            if not role.mentionable:
                try:
                    await role.edit(mentionable=True, reason="Pinging role via /ping command")
                    roles_to_reset.append(role)
                except discord.Forbidden:
                    pass  # No permission to edit — still attempt the mention

        mention_str = " ".join(mention_parts) if mention_parts else None

        try:
            await self.target_channel.send(content=mention_str, embed=self.embed)

            # Reset mentionability for any roles we temporarily enabled
            if roles_to_reset:
                await asyncio.sleep(1)
                for role in roles_to_reset:
                    try:
                        await role.edit(mentionable=False, reason="Resetting role mentionability after /ping")
                    except discord.Forbidden:
                        pass

            if self.target_channel.id == self.source_channel_id:
                await interaction.followup.send(
                    "✅ Your ping has been posted in this channel.", ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"✅ Your post has been successfully published in {self.target_channel.mention}",
                    ephemeral=True,
                )
        except discord.Forbidden:
            await interaction.followup.send(
                f"❌ Error: I do not have permission to send messages in {self.target_channel.mention}.",
                ephemeral=True,
            )

        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="✖️", row=1)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("❌ Ping cancelled.", ephemeral=True)
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
        # Create tables if they don't exist
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS enforced_channels (
                    channel_id INTEGER PRIMARY KEY,
                    mode TEXT DEFAULT 'strict',
                    mode_parameters TEXT
                )
            """)

            # Check for columns if table already existed (migration)
            cursor.execute("PRAGMA table_info(enforced_channels)")
            columns = [info[1] for info in cursor.fetchall()]
            if "mode" not in columns:
                cursor.execute("ALTER TABLE enforced_channels ADD COLUMN mode TEXT DEFAULT 'strict'")
            if "mode_parameters" not in columns:
                cursor.execute("ALTER TABLE enforced_channels ADD COLUMN mode_parameters TEXT")

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

            # New table for named user reminders
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS named_user_reminders (
                    user_id INTEGER PRIMARY KEY,
                    reminder_message TEXT,
                    punishment_type TEXT DEFAULT 'none',
                    punishment_value INTEGER DEFAULT 0
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

    def _get_enforcement_info(self, channel_id: int):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT mode, mode_parameters FROM enforced_channels WHERE channel_id = ?",
                (channel_id,),
            )
            return cursor.fetchone()

    def _is_enforced(self, channel_id: int) -> bool:
        return self._get_enforcement_info(channel_id) is not None

    def _set_enforced(self, channel_id: int, mode: str = "strict", parameters: str = None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if mode == "disabled":
                cursor.execute("DELETE FROM enforced_channels WHERE channel_id = ?", (channel_id,))
            else:
                cursor.execute(
                    """
                    INSERT INTO enforced_channels (channel_id, mode, mode_parameters) 
                    VALUES (?, ?, ?)
                    ON CONFLICT(channel_id) DO UPDATE SET 
                        mode=excluded.mode, 
                        mode_parameters=excluded.mode_parameters
                    """,
                    (channel_id, mode, parameters),
                )
            conn.commit()

    def _set_user_reminder(self, user_id: int, message: str, p_type: str = "none", p_value: int = 0):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if message is None:
                cursor.execute("DELETE FROM named_user_reminders WHERE user_id = ?", (user_id,))
            else:
                cursor.execute(
                    """
                    INSERT INTO named_user_reminders (user_id, reminder_message, punishment_type, punishment_value) 
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET 
                        reminder_message=excluded.reminder_message,
                        punishment_type=excluded.punishment_type,
                        punishment_value=excluded.punishment_value
                    """,
                    (user_id, message, p_type, p_value),
                )
            conn.commit()

    def _get_user_reminder(self, user_id: int):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT reminder_message, punishment_type, punishment_value "
                "FROM named_user_reminders WHERE user_id = ?",
                (user_id,),
            )
            return cursor.fetchone()

    @app_commands.command(
        name="enforce_channel",
        description="Configure message enforcement for the current channel.",
    )
    @app_commands.describe(
        mode="Enforcement level: Strict, Warn Only, Timed Delete, or Grace Period.",
        parameters="Optional settings (e.g., delay in seconds for Timed Delete, or date for Grace Period).",
    )
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="Strict (Instant Delete)", value="strict"),
            app_commands.Choice(name="Warn Only (No Delete)", value="warn_only"),
            app_commands.Choice(name="Timed Delete", value="timed_delete"),
            app_commands.Choice(name="Grace Period (Warning)", value="grace_period"),
            app_commands.Choice(name="Disabled", value="disabled"),
        ]
    )
    @app_commands.check(has_staff_or_admin)
    async def enforce_channel(
        self,
        interaction: discord.Interaction,
        mode: app_commands.Choice[str],
        parameters: str = None,
    ):
        """Configure message enforcement for the current channel."""
        self._set_enforced(interaction.channel_id, mode.value, parameters)

        status = f"set to **{mode.name}**" if mode.value != "disabled" else "disabled"
        param_hint = f" with parameters: `{parameters}`" if parameters else ""
        await interaction.response.send_message(
            f"Message enforcement has been {status}{param_hint} for this channel.", ephemeral=True
        )

        # Log admin action
        embed = discord.Embed(
            title="Enforcement Configuration Changed",
            description=(
                f"**Channel:** {interaction.channel.mention}\n"
                f"**Mode:** {mode.name}\n"
                f"**Parameters:** `{parameters or 'None'}`\n"
                f"**Staff:** {interaction.user.mention}"
            ),
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )
        await self.bot.log_admin_action(embed)

    @app_commands.command(
        name="enforcer_user_reminder",
        description="Set a custom reminder message and punishment for a specific user.",
    )
    @app_commands.describe(
        user="The user to target.",
        message="The reminder message (None to remove).",
        punishment_type="Punishment type (optional).",
        punishment_value="Punishment value (e.g., timeout seconds).",
    )
    @app_commands.choices(
        punishment_type=[
            app_commands.Choice(name="None", value="none"),
            app_commands.Choice(name="Timeout", value="timeout"),
        ]
    )
    @app_commands.check(has_staff_or_admin)
    async def enforcer_user_reminder(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        message: str = None,
        punishment_type: app_commands.Choice[str] = None,
        punishment_value: int = 0,
    ):
        """Set a custom reminder for a named user."""
        p_type = punishment_type.value if punishment_type else "none"
        self._set_user_reminder(user.id, message, p_type, punishment_value)

        if message is None:
            await interaction.response.send_message(
                f"Removed custom reminder for {user.mention}.", ephemeral=True
            )
        else:
            p_msg = f" (Punishment: {p_type} for {punishment_value}s)" if p_type != "none" else ""
            await interaction.response.send_message(
                f"Custom reminder set for {user.mention}: {message}{p_msg}", ephemeral=True
            )

        # Log admin action
        embed = discord.Embed(
            title="User Reminder Updated",
            description=(
                f"**User:** {user.mention} ({user.id})\n"
                f"**Message:** {message or 'REMOVED'}\n"
                f"**Punishment:** {p_type} ({punishment_value}s)\n"
                f"**Staff:** {interaction.user.mention}"
            ),
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )
        await self.bot.log_admin_action(embed)

    @app_commands.command(
        name="scanz_format", description="Interactive setup for the channel's enforced log format."
    )
    @app_commands.check(has_staff_or_admin)
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

    @app_commands.command(name="set_ping_target", description="Set a default target channel for pings.")
    @app_commands.check(has_staff_or_admin)
    async def set_ping_target(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set a default target channel for pings."""
        self._set_post_target("Ping", channel.id)
        await interaction.response.send_message(
            f"Successfully set the default channel for pings to {channel.mention}.",
            ephemeral=True,
        )

        # Log admin action
        embed = discord.Embed(
            title="Log Configuration Updated",
            description=(
                f"**Action:** Ping Target Channel set to {channel.mention}\n"
                f"**Staff:** {interaction.user.mention}"
            ),
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )
        await self.bot.log_admin_action(embed)

    @app_commands.command(
        name="scanz_subscriptions",
        description="Post the role subscription message in the current channel.",
    )
    @app_commands.check(has_staff_or_admin)
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

        # Check for named user reminders
        reminder_info = self._get_user_reminder(message.author.id)
        if reminder_info:
            reminder_text, p_type, p_value = reminder_info

            # Send custom reminder
            try:
                await message.author.send(reminder_text)
            except discord.Forbidden:
                await message.channel.send(f"{message.author.mention}, {reminder_text}", delete_after=15)

            # Apply punishment
            if p_type == "timeout" and p_value > 0 and isinstance(message.author, discord.Member):
                try:
                    import datetime

                    await message.author.timeout(
                        datetime.timedelta(seconds=p_value),
                        reason="Enforcer custom punishment",
                    )

                    # Log punishment
                    embed = discord.Embed(
                        title="User Punishment Applied",
                        description=(
                            f"**User:** {message.author.mention} ({message.author.id})\n"
                            f"**Action:** Timeout ({p_value}s)\n"
                            f"**Reason:** Triggered named user reminder penalty."
                        ),
                        color=discord.Color.dark_red(),
                        timestamp=discord.utils.utcnow(),
                    )
                    await self.bot.log_admin_action(embed)
                except Exception as e:
                    print(f"Failed to timeout user {message.author.id}: {e}")

        # Check if the channel is enforced
        enforcement_info = self._get_enforcement_info(message.channel.id)
        if not enforcement_info:
            return

        mode, mode_params = enforcement_info

        # Bypass enforcement for specific roles
        if isinstance(message.author, discord.Member):
            allowed_roles = {"officer", "officers", "custodian", "custodians", "scanz developer"}
            user_roles = {role.name.lower() for role in message.author.roles}
            if allowed_roles & user_roles:
                return

        # Handle different modes
        warning_template = CONFIG.get("messages", {}).get(
            "warning_text",
            (
                "Your message in {channel} was deleted because the channel is strictly formatted.\n"
                "Please use the `/ping` command to submit requests."
            ),
        )
        warning_text = warning_template.replace("{channel}", message.channel.mention)

        if mode == "strict":
            try:
                await message.delete()
                try:
                    await message.author.send(warning_text)
                except discord.Forbidden:
                    await message.channel.send(f"{message.author.mention}, {warning_text}", delete_after=10)

                # Log to admin channel
                embed = discord.Embed(
                    title="Strict Enforcement: Message Deleted",
                    description=(
                        f"**User:** {message.author.mention} ({message.author.id})\n"
                        f"**Channel:** {message.channel.mention}\n"
                        f"**Content Snippet:** {message.content[:200] if message.content else 'None'}"
                    ),
                    color=discord.Color.red(),
                    timestamp=discord.utils.utcnow(),
                )
                await self.bot.log_admin_action(embed)
            except (discord.NotFound, discord.Forbidden):
                pass

        elif mode == "warn_only":
            warn_msg = (
                f"{message.author.mention}, **Notice:** This channel will eventually "
                "require `/ping`. Please start practicing now!"
            )
            await message.channel.send(warn_msg, delete_after=15)

        elif mode == "timed_delete":
            try:
                delay = int(mode_params) if mode_params and mode_params.isdigit() else 60
            except ValueError:
                delay = 60

            await message.channel.send(
                f"{message.author.mention}, your message will be deleted in {delay} "
                "seconds. This channel requires `/ping`.",
                delete_after=10,
            )
            await asyncio.sleep(delay)
            try:
                await message.delete()
            except (discord.NotFound, discord.Forbidden):
                pass

        elif mode == "grace_period":
            # Parameters might be a date or "X days"
            msg = (
                f"{message.author.mention}, **Channel Transition Warning:** In "
                f"{mode_params or 'a few'} days, this channel will transition to "
                "**Strict Enforcement**. Only `/ping` messages will be allowed."
            )
            await message.channel.send(msg, delete_after=20)

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

        # Build the role-selection view and let the user choose which roles to ping
        ping_roles = CONFIG.get("ping_roles", {})
        has_configured_roles = any(v.get("role_id", 0) != 0 for v in ping_roles.values())

        view = PingRoleSelectView(embed, target_channel, interaction.channel_id or 0)

        if has_configured_roles:
            prompt = (
                "**Select the roles you want to ping**, then click **Post Ping**.\n"
                "Leave the dropdown untouched to post without any role mention."
            )
        else:
            prompt = (
                "⚠️ No ping roles are configured yet (all `role_id` values are `0` in "
                "`enforcer_template.json`).\n\nClick **Post Ping** to post without a mention, "
                "or **Cancel** to abort."
            )

        await interaction.response.send_message(prompt, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(MessageEnforcer(bot))
