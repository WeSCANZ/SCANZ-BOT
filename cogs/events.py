import os
import re
import sqlite3
from datetime import datetime, timedelta

import discord
import pytz
from discord import app_commands
from discord.ext import commands

from utils.checks import has_staff_or_admin

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "events.db")

TIMEZONE_MAP = {
    "UTC": "UTC",
    "GMT": "UTC",
    "ICT": "Asia/Bangkok",
    "AWST": "Australia/Perth",
    "AEST": "Australia/Sydney",
    "AET": "Australia/Sydney",
    "AEDT": "Australia/Sydney",
    "NZST": "Pacific/Auckland",
    "NZT": "Pacific/Auckland",
    "NZDT": "Pacific/Auckland",
    "SGT": "Asia/Singapore",
    "HKT": "Asia/Hong_Kong",
    "JST": "Asia/Tokyo",
    "CST": "Asia/Shanghai",
    "PHT": "Asia/Manila",
}


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = _get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id    INTEGER NOT NULL,
            channel_id  INTEGER,
            message_id  INTEGER,
            creator_id  INTEGER NOT NULL,
            title       TEXT NOT NULL,
            description TEXT DEFAULT '',
            start_time  TEXT NOT NULL,
            duration    TEXT DEFAULT '',
            location    TEXT DEFAULT '',
            image_url   TEXT DEFAULT '',
            status      TEXT DEFAULT 'active'
        );
        CREATE TABLE IF NOT EXISTS event_roles (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id      INTEGER NOT NULL,
            role_name     TEXT NOT NULL,
            max_slots     INTEGER,
            display_order INTEGER DEFAULT 0,
            FOREIGN KEY (event_id) REFERENCES events(id)
        );
        CREATE TABLE IF NOT EXISTS event_rsvps (
            event_id  INTEGER NOT NULL,
            user_id   INTEGER NOT NULL,
            role_id   INTEGER NOT NULL,
            rsvp_time TEXT NOT NULL,
            PRIMARY KEY (event_id, user_id),
            FOREIGN KEY (event_id) REFERENCES events(id),
            FOREIGN KEY (role_id)  REFERENCES event_roles(id)
        );
        CREATE TABLE IF NOT EXISTS event_config (
            guild_id          INTEGER PRIMARY KEY,
            events_channel_id INTEGER
        );
    """)
    conn.commit()

    # Schema migrations - add new columns if they don't exist
    cursor = conn.cursor()
    for col_name, col_type in [("description", "TEXT DEFAULT ''"), ("image_url", "TEXT DEFAULT ''")]:
        try:
            cursor.execute(f"ALTER TABLE events ADD COLUMN {col_name} {col_type}")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists

    conn.close()


def _parse_datetime(date_str: str) -> datetime | None:
    date_str = date_str.strip()
    tz = pytz.UTC

    utc_match = re.search(r"UTC([+-]\d+)", date_str, re.IGNORECASE)
    if utc_match:
        offset = int(utc_match.group(1))
        tz = pytz.FixedOffset(offset * 60)
        date_str = re.sub(r"UTC[+-]\d+", "", date_str).strip()
    else:
        for abbr, tz_name in TIMEZONE_MAP.items():
            if re.search(r"\b" + abbr + r"\b", date_str, re.IGNORECASE):
                tz = pytz.timezone(tz_name)
                date_str = re.sub(r"\b" + abbr + r"\b", "", date_str, flags=re.IGNORECASE).strip()
                break

    for fmt in (
        "%d-%m-%Y %H:%M",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M",
        "%d %B %Y %H:%M",
        "%B %d %Y %H:%M",
        "%Y-%m-%d %I:%M %p",
    ):
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return tz.localize(dt)
        except ValueError:
            continue
    return None


def _parse_duration(text: str) -> timedelta:
    hours = re.search(r"(\d+)\s*h(?:ours?)?", text, re.IGNORECASE)
    minutes = re.search(r"(\d+)\s*m(?:in(?:utes?)?)?", text, re.IGNORECASE)
    h = int(hours.group(1)) if hours else 0
    m = int(minutes.group(1)) if minutes else 0
    return timedelta(hours=h, minutes=m) if (h or m) else timedelta(hours=2)


def _parse_roles(text: str) -> list[dict]:
    roles = []
    for i, part in enumerate(text.split(",")):
        part = part.strip()
        if not part:
            continue
        max_slots = None
        if ":" in part:
            name, slots = part.rsplit(":", 1)
            if slots.strip().isdigit():
                max_slots = int(slots.strip())
                part = name.strip()
        roles.append({"name": part, "max_slots": max_slots, "order": i})
    return roles


def _build_embed(event: dict, roles: list[dict], rsvps_by_role: dict[int, list[str]]) -> discord.Embed:
    embed = discord.Embed(title=event["title"], color=0x5865F2)

    if event.get("description"):
        embed.description = event["description"]

    try:
        dt = datetime.fromisoformat(event["start_time"])
        ts = int(dt.timestamp())
        embed.add_field(name="Time (Your Timezone)", value=f"<t:{ts}:F>\n<t:{ts}:R>", inline=True)
    except Exception:
        embed.add_field(name="Time", value=event["start_time"], inline=True)

    if event.get("location"):
        embed.add_field(name="Location", value=event["location"], inline=False)

    for role in roles:
        rid = role["id"]
        members = rsvps_by_role.get(rid, [])
        slots = role.get("max_slots")
        slot_str = f"({len(members)}/{slots})" if slots else f"({len(members)})"
        field_value = "\n".join(f"• {m}" for m in members) or "*No sign-ups yet*"
        embed.add_field(name=f"**{role['role_name']}** {slot_str}", value=field_value, inline=True)

    if event.get("image_url"):
        embed.set_image(url=event["image_url"])

    embed.set_footer(text=f"Event ID: {event['id']}")
    return embed


async def _get_event_data(event_id: int, guild: discord.Guild) -> tuple[dict | None, list, dict]:
    conn = _get_db()
    event = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        conn.close()
        return None, [], {}

    event = dict(event)
    roles = [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM event_roles WHERE event_id = ? ORDER BY display_order", (event_id,)
        ).fetchall()
    ]
    rsvps = conn.execute(
        "SELECT role_id, user_id FROM event_rsvps WHERE event_id = ?", (event_id,)
    ).fetchall()
    conn.close()

    rsvps_by_role: dict[int, list[str]] = {}
    for r in rsvps:
        member = guild.get_member(r["user_id"])
        name = member.display_name if member else f"User {r['user_id']}"
        rsvps_by_role.setdefault(r["role_id"], []).append(name)

    return event, roles, rsvps_by_role


async def _update_event_message(bot: commands.Bot, guild: discord.Guild, event_id: int):
    event, roles, rsvps_by_role = await _get_event_data(event_id, guild)
    if not event or not event.get("message_id"):
        return

    channel = guild.get_channel(event["channel_id"])
    if not channel:
        return

    try:
        msg = await channel.fetch_message(event["message_id"])
        embed = _build_embed(event, roles, rsvps_by_role)
        view = EventView(event_id, roles)
        await msg.edit(embed=embed, view=view)
    except (discord.NotFound, discord.Forbidden):
        pass


# ── UI Components ──────────────────────────────────────────────────────────────


class EventRSVPSelect(discord.ui.Select):
    def __init__(self, event_id: int, roles: list[dict]):
        self.event_id = event_id
        options = [
            discord.SelectOption(
                label=r["role_name"][:100],
                value=str(r["id"]),
                description=(f"Max: {r['max_slots']} slots" if r.get("max_slots") else "Unlimited slots")[:100],
            )
            for r in roles[:25]
        ]
        super().__init__(
            custom_id=f"event_rsvp:{event_id}",
            placeholder="Select RSVP",
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        role_id = int(self.values[0])
        conn = _get_db()

        event = conn.execute("SELECT status FROM events WHERE id = ?", (self.event_id,)).fetchone()
        if not event or event["status"] != "active":
            conn.close()
            return await interaction.response.send_message("This event is no longer active.", ephemeral=True)

        role = conn.execute("SELECT * FROM event_roles WHERE id = ?", (role_id,)).fetchone()
        if not role:
            conn.close()
            return await interaction.response.send_message("Invalid role.", ephemeral=True)

        if role["max_slots"]:
            taken = conn.execute(
                "SELECT COUNT(*) FROM event_rsvps WHERE role_id = ? AND user_id != ?",
                (role_id, interaction.user.id),
            ).fetchone()[0]
            if taken >= role["max_slots"]:
                conn.close()
                return await interaction.response.send_message(
                    f"**{role['role_name']}** is full ({role['max_slots']}/{role['max_slots']}).",
                    ephemeral=True,
                )

        conn.execute(
            """
            INSERT INTO event_rsvps (event_id, user_id, role_id, rsvp_time) VALUES (?, ?, ?, ?)
            ON CONFLICT(event_id, user_id) DO UPDATE SET role_id=excluded.role_id, rsvp_time=excluded.rsvp_time
            """,
            (self.event_id, interaction.user.id, role_id, datetime.utcnow().isoformat()),
        )
        conn.commit()
        conn.close()

        await interaction.response.send_message(f"Signed up as **{role['role_name']}**!", ephemeral=True)
        await _update_event_message(interaction.client, interaction.guild, self.event_id)


class EventUnRSVPButton(discord.ui.Button):
    def __init__(self, event_id: int):
        self.event_id = event_id
        super().__init__(
            label="UnRSVP",
            style=discord.ButtonStyle.danger,
            custom_id=f"event_unrsvp:{event_id}",
        )

    async def callback(self, interaction: discord.Interaction):
        conn = _get_db()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM event_rsvps WHERE event_id = ? AND user_id = ?",
            (self.event_id, interaction.user.id),
        )
        affected = cursor.rowcount
        conn.commit()
        conn.close()

        if not affected:
            return await interaction.response.send_message("You're not signed up for this event.", ephemeral=True)

        await interaction.response.send_message("You've been removed from the event.", ephemeral=True)
        await _update_event_message(interaction.client, interaction.guild, self.event_id)


class EventView(discord.ui.View):
    def __init__(self, event_id: int, roles: list[dict]):
        super().__init__(timeout=None)
        if roles:
            self.add_item(EventRSVPSelect(event_id, roles))
        self.add_item(EventUnRSVPButton(event_id))


# ── Modal ──────────────────────────────────────────────────────────────────────


class EventCreateModal(discord.ui.Modal, title="Create Event"):
    event_title = discord.ui.TextInput(
        label="Event Title",
        placeholder="Salvage Op - Nyx System",
        max_length=100,
    )
    datetime_input = discord.ui.TextInput(
        label="Date & Time (DD-MM-YYYY HH:MM TIMEZONE)",
        placeholder="12-05-2026 04:00 AWST  (or UTC, ICT, SGT, UTC+8 …)",
        max_length=60,
    )
    location = discord.ui.TextInput(
        label="Location",
        placeholder="Nyx > Stanton Gateway",
        required=False,
        max_length=100,
    )
    description = discord.ui.TextInput(
        label="Description (optional)",
        placeholder="Event details, objectives, requirements, etc.",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500,
    )
    image_url = discord.ui.TextInput(
        label="Image URL (optional)",
        placeholder="https://example.com/image.jpg",
        required=False,
        max_length=200,
    )
    roles_input = discord.ui.TextInput(
        label="Roles  (Name:slots or Name, comma-separated)",
        placeholder="Salvage|Reclaimer:3, Logistics:6, Combat:6, Put me anywhere!",
        style=discord.TextStyle.paragraph,
        max_length=500,
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)

            dt = _parse_datetime(self.datetime_input.value)
            if not dt:
                return await interaction.followup.send(
                    "Could not parse the date/time.\n"
                    "Use format: `DD-MM-YYYY HH:MM TIMEZONE`\n"
                    "Example: `12-05-2026 04:00 AWST` or `12-05-2026 04:00 UTC+8`",
                    ephemeral=True,
                )

            roles_data = _parse_roles(self.roles_input.value)
            if not roles_data:
                return await interaction.followup.send("No valid roles found.", ephemeral=True)

            conn = _get_db()
            config = conn.execute(
                "SELECT events_channel_id FROM event_config WHERE guild_id = ?", (interaction.guild_id,)
            ).fetchone()

            target_channel = None
            if config and config["events_channel_id"]:
                target_channel = interaction.guild.get_channel(config["events_channel_id"])
            if not target_channel:
                target_channel = interaction.channel

            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO events (guild_id, creator_id, title, description, start_time, location, image_url) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    interaction.guild_id,
                    interaction.user.id,
                    self.event_title.value,
                    self.description.value or "",
                    dt.isoformat(),
                    self.location.value or "",
                    self.image_url.value or "",
                ),
            )
            event_id = cursor.lastrowid

            for rd in roles_data:
                cursor.execute(
                    "INSERT INTO event_roles (event_id, role_name, max_slots, display_order) VALUES (?, ?, ?, ?)",
                    (event_id, rd["name"], rd.get("max_slots"), rd["order"]),
                )
            conn.commit()

            db_roles = [
                dict(r)
                for r in conn.execute(
                    "SELECT * FROM event_roles WHERE event_id = ? ORDER BY display_order", (event_id,)
                ).fetchall()
            ]
            event = dict(conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone())

            embed = _build_embed(event, db_roles, {})
            view = EventView(event_id, db_roles)
            msg = await target_channel.send(embed=embed, view=view)

            conn.execute(
                "UPDATE events SET message_id = ?, channel_id = ? WHERE id = ?",
                (msg.id, msg.channel.id, event_id),
            )
            conn.commit()
            conn.close()

            await interaction.followup.send(f"Event created! [Jump to event]({msg.jump_url})", ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)


# ── Cog ───────────────────────────────────────────────────────────────────────


class EventCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        _init_db()

    async def cog_load(self):
        conn = _get_db()
        rows = conn.execute(
            """
            SELECT e.id, e.message_id,
                   r.id AS rid, r.role_name, r.max_slots, r.display_order
            FROM events e
            LEFT JOIN event_roles r ON r.event_id = e.id
            WHERE e.status = 'active'
            ORDER BY e.id, r.display_order
            """
        ).fetchall()
        conn.close()

        events_roles: dict[int, tuple[int | None, list]] = {}
        for row in rows:
            eid = row["id"]
            if eid not in events_roles:
                events_roles[eid] = (row["message_id"], [])
            if row["rid"]:
                events_roles[eid][1].append(
                    {"id": row["rid"], "role_name": row["role_name"], "max_slots": row["max_slots"]}
                )

        for event_id, (message_id, roles) in events_roles.items():
            view = EventView(event_id, roles)
            self.bot.add_view(view, message_id=message_id)

    # ── Commands ──────────────────────────────────────────────────────────────

    @app_commands.command(name="create_event", description="Create a new org event with RSVP roles")
    @app_commands.check(has_staff_or_admin)
    async def create_event(self, interaction: discord.Interaction):
        await interaction.response.send_modal(EventCreateModal())

    @app_commands.command(name="cancel_event", description="Cancel an active event")
    @app_commands.describe(event_id="The event ID to cancel")
    @app_commands.check(has_staff_or_admin)
    async def cancel_event(self, interaction: discord.Interaction, event_id: int):
        conn = _get_db()
        event = conn.execute(
            "SELECT * FROM events WHERE id = ? AND guild_id = ?", (event_id, interaction.guild_id)
        ).fetchone()

        if not event:
            conn.close()
            return await interaction.response.send_message("Event not found.", ephemeral=True)
        if event["status"] != "active":
            conn.close()
            return await interaction.response.send_message("Event is already cancelled or completed.", ephemeral=True)

        conn.execute("UPDATE events SET status = 'cancelled' WHERE id = ?", (event_id,))
        conn.commit()
        event = dict(event)
        conn.close()

        if event.get("message_id") and event.get("channel_id"):
            ch = interaction.guild.get_channel(event["channel_id"])
            if ch:
                try:
                    msg_obj = await ch.fetch_message(event["message_id"])
                    if msg_obj.embeds:
                        emb = msg_obj.embeds[0].copy()
                        emb.colour = discord.Color.red()
                        emb.title = f"[CANCELLED] {emb.title}"
                        await msg_obj.edit(embed=emb, view=None)
                except (discord.NotFound, discord.Forbidden):
                    pass

        await interaction.response.send_message(f"Event #{event_id} has been cancelled.", ephemeral=True)

    @app_commands.command(name="set_event_image", description="Set an image for an existing event")
    @app_commands.describe(event_id="Event ID", image_url="Direct URL to the image")
    @app_commands.check(has_staff_or_admin)
    async def set_event_image(self, interaction: discord.Interaction, event_id: int, image_url: str):
        conn = _get_db()
        result = conn.execute(
            "UPDATE events SET image_url = ? WHERE id = ? AND guild_id = ? AND status = 'active'",
            (image_url, event_id, interaction.guild_id),
        )
        conn.commit()
        conn.close()

        if result.rowcount == 0:
            return await interaction.response.send_message("Event not found or already inactive.", ephemeral=True)

        await interaction.response.send_message("Image updated!", ephemeral=True)
        await _update_event_message(self.bot, interaction.guild, event_id)

    @app_commands.command(name="set_event_duration", description="Set or override the duration of an event")
    @app_commands.describe(event_id="Event ID", duration="Duration (e.g. '2 hours 30 minutes')")
    @app_commands.check(has_staff_or_admin)
    async def set_event_duration(self, interaction: discord.Interaction, event_id: int, duration: str):
        conn = _get_db()
        result = conn.execute(
            "UPDATE events SET duration = ? WHERE id = ? AND guild_id = ? AND status = 'active'",
            (duration, event_id, interaction.guild_id),
        )
        conn.commit()
        conn.close()

        if result.rowcount == 0:
            return await interaction.response.send_message("Event not found or already inactive.", ephemeral=True)

        await interaction.response.send_message(f"Duration updated to `{duration}`!", ephemeral=True)

    @app_commands.command(name="set_events_channel", description="Set the default channel for posting events")
    @app_commands.describe(channel="Channel where events will be posted")
    @app_commands.check(has_staff_or_admin)
    async def set_events_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        conn = _get_db()
        conn.execute(
            """
            INSERT INTO event_config (guild_id, events_channel_id) VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET events_channel_id = excluded.events_channel_id
            """,
            (interaction.guild_id, channel.id),
        )
        conn.commit()
        conn.close()

        await interaction.response.send_message(f"Events will now be posted in {channel.mention}.", ephemeral=True)

    @app_commands.command(name="list_events", description="List upcoming active events")
    async def list_events(self, interaction: discord.Interaction):
        conn = _get_db()
        events = conn.execute(
            "SELECT id, title, start_time, location FROM events WHERE guild_id = ? AND status = 'active' ORDER BY start_time",
            (interaction.guild_id,),
        ).fetchall()
        conn.close()

        if not events:
            return await interaction.response.send_message("No upcoming events.", ephemeral=True)

        embed = discord.Embed(title="Upcoming Events", color=0x5865F2)
        for ev in events:
            try:
                ts = int(datetime.fromisoformat(ev["start_time"]).timestamp())
                time_str = f"<t:{ts}:F>"
            except Exception:
                time_str = ev["start_time"]
            embed.add_field(
                name=f"#{ev['id']} — {ev['title']}",
                value=f"{time_str}\n📍 {ev['location'] or 'TBD'}",
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(EventCog(bot))
