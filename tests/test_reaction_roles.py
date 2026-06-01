"""
Tests for cogs/reaction_roles.py
Covers:
  - Issue #16 fix: setup_reaction_role has @app_commands.default_permissions(manage_roles=True)
  - DB initialisation (_setup_db) and restore (_load_from_db)
  - setup_reaction_role command persists mapping in memory and SQLite
  - on_raw_reaction_add assigns roles, skips bots, ignores unknown messages/emojis
  - on_raw_reaction_remove removes roles, skips bots, ignores unknown messages/emojis
"""

import os
import sqlite3
import sys
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from discord import app_commands

# Make sure the project root is importable regardless of where pytest is run.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cogs.reaction_roles import ReactionRoles  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def cog(tmp_path):
    """
    Return a ReactionRoles cog instance backed by a temporary SQLite database.

    We bypass __init__ so we can point db_path at a safe temp directory without
    touching the real 'data/' folder.
    """
    bot = MagicMock()
    # Mock log_admin_action since it might be awaited in setup_reaction_role
    bot.log_admin_action = AsyncMock()
    instance = ReactionRoles.__new__(ReactionRoles)
    instance.bot = bot
    instance.db_path = str(tmp_path / "reaction_roles.db")
    instance.reaction_roles = {}
    instance._setup_db()
    instance._load_from_db()
    return instance


def _payload(message_id: int, emoji_str: str, guild_id: int = 1, user_id: int = 2) -> MagicMock:
    """Return a minimal RawReactionActionEvent-style payload mock."""
    p = MagicMock()
    p.message_id = message_id
    p.guild_id = guild_id
    p.user_id = user_id
    # str(payload.emoji) must return the emoji string.
    p.emoji.__str__ = MagicMock(return_value=emoji_str)
    return p


def _member(*, is_bot: bool = False) -> MagicMock:
    """Return a minimal Member mock."""
    m = MagicMock()
    m.bot = is_bot
    m.add_roles = AsyncMock()
    m.remove_roles = AsyncMock()
    return m


def _guild(role: MagicMock, member: MagicMock) -> MagicMock:
    """Return a minimal Guild mock wired to the given role and member."""
    g = MagicMock()
    g.get_role.return_value = role
    g.get_member.return_value = member
    return g


# ---------------------------------------------------------------------------
# Issue #16 — permission decorator
# ---------------------------------------------------------------------------


class TestPermissions:
    def test_command_is_app_command(self):
        """setup_reaction_role must be registered as an app_commands.Command."""
        assert isinstance(ReactionRoles.setup_reaction_role, app_commands.Command)

    def test_default_permissions_is_set(self):
        """setup_reaction_role must declare default_permissions (issue #16)."""
        cmd = ReactionRoles.setup_reaction_role
        assert cmd.default_permissions is not None, (
            "default_permissions is None — the @app_commands.default_permissions "
            "decorator is missing (issue #16)"
        )

    def test_manage_roles_required(self):
        """default_permissions must require manage_roles=True."""
        perms = ReactionRoles.setup_reaction_role.default_permissions
        assert perms is not None, "default_permissions is None — cannot check manage_roles"
        assert perms.manage_roles is True, (
            "manage_roles is not True — any user can invoke /setup_reaction_role"
        )

    def test_administrator_not_required(self):
        """
        We chose manage_roles over administrator (least-privilege).
        If someone switches to administrator=True this test should be updated
        intentionally, not silently.
        """
        perms = ReactionRoles.setup_reaction_role.default_permissions
        assert perms is not None, "default_permissions is None — cannot check administrator"
        assert perms.administrator is False, (
            "Prefer manage_roles over administrator to follow least-privilege principle"
        )


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


class TestDatabase:
    def test_setup_db_creates_table(self, cog):
        """_setup_db() must create the reaction_roles table."""
        with sqlite3.connect(cog.db_path) as conn:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='reaction_roles'"
            ).fetchone()
        assert row is not None, "Table 'reaction_roles' was not created"

    def test_load_from_db_single_row(self, cog):
        """_load_from_db() must restore a single emoji→role mapping."""
        with sqlite3.connect(cog.db_path) as conn:
            conn.execute("INSERT INTO reaction_roles VALUES (?, ?, ?)", (12345, "👍", 67890))
            conn.commit()

        cog.reaction_roles = {}
        cog._load_from_db()

        assert cog.reaction_roles.get(12345, {}).get("👍") == 67890

    def test_load_from_db_multiple_rows(self, cog):
        """_load_from_db() must handle multiple message/emoji pairs."""
        rows = [(1, "👍", 100), (1, "👎", 200), (2, "🎉", 300)]
        with sqlite3.connect(cog.db_path) as conn:
            conn.executemany("INSERT INTO reaction_roles VALUES (?, ?, ?)", rows)
            conn.commit()

        cog.reaction_roles = {}
        cog._load_from_db()

        assert cog.reaction_roles[1]["👍"] == 100
        assert cog.reaction_roles[1]["👎"] == 200
        assert cog.reaction_roles[2]["🎉"] == 300

    def test_load_from_db_empty(self, cog):
        """_load_from_db() on an empty DB must leave reaction_roles empty."""
        cog._load_from_db()
        assert cog.reaction_roles == {}


# ---------------------------------------------------------------------------
# setup_reaction_role command
# ---------------------------------------------------------------------------


class TestSetupReactionRole:
    def _make_interaction(self, msg_id: int = 99999) -> MagicMock:
        interaction = MagicMock()
        interaction.response.send_message = AsyncMock()
        msg = MagicMock()
        msg.id = msg_id
        msg.add_reaction = AsyncMock()
        interaction.original_response = AsyncMock(return_value=msg)
        return interaction

    def _make_role(self, role_id: int = 111) -> MagicMock:
        role = MagicMock(spec=discord.Role)
        role.id = role_id
        role.mention = f"<@&{role_id}>"
        return role

    async def test_stores_mapping_in_memory(self, cog):
        """Command must write the emoji→role_id mapping to self.reaction_roles."""
        interaction = self._make_interaction(msg_id=10001)
        role = self._make_role(role_id=555)

        await cog.setup_reaction_role.callback(cog, interaction, role, "👍", "React for role!")

        assert cog.reaction_roles.get(10001, {}).get("👍") == 555

    async def test_stores_mapping_in_db(self, cog):
        """Command must persist the mapping to the SQLite database."""
        interaction = self._make_interaction(msg_id=10002)
        role = self._make_role(role_id=666)

        await cog.setup_reaction_role.callback(cog, interaction, role, "🎉", "Party role!")

        with sqlite3.connect(cog.db_path) as conn:
            row = conn.execute(
                "SELECT role_id FROM reaction_roles WHERE message_id=? AND emoji=?",
                (10002, "🎉"),
            ).fetchone()
        assert row is not None and row[0] == 666

    async def test_adds_reaction_to_message(self, cog):
        """Command must add the emoji reaction to the posted embed message."""
        interaction = self._make_interaction(msg_id=10003)
        role = self._make_role()

        await cog.setup_reaction_role.callback(cog, interaction, role, "⭐", "Star role!")

        msg = await interaction.original_response()
        msg.add_reaction.assert_called_once_with("⭐")

    async def test_upsert_overwrites_existing_role(self, cog):
        """Calling the command twice for the same message+emoji must overwrite."""
        interaction1 = self._make_interaction(msg_id=10004)
        interaction2 = self._make_interaction(msg_id=10004)
        role_a = self._make_role(role_id=10)
        role_b = self._make_role(role_id=20)

        await cog.setup_reaction_role.callback(cog, interaction1, role_a, "👍", "First")
        await cog.setup_reaction_role.callback(cog, interaction2, role_b, "👍", "Second")

        assert cog.reaction_roles[10004]["👍"] == 20

        with sqlite3.connect(cog.db_path) as conn:
            row = conn.execute(
                "SELECT role_id FROM reaction_roles WHERE message_id=? AND emoji=?",
                (10004, "👍"),
            ).fetchone()
        assert row[0] == 20


# ---------------------------------------------------------------------------
# on_raw_reaction_add
# ---------------------------------------------------------------------------


class TestOnRawReactionAdd:
    async def test_assigns_role_to_human_member(self, cog):
        """Reaction add must assign the mapped role to a non-bot member."""
        cog.reaction_roles = {12345: {"👍": 67890}}

        member = _member(is_bot=False)
        role = MagicMock()
        cog.bot.get_guild.return_value = _guild(role, member)

        await cog.on_raw_reaction_add(_payload(12345, "👍"))

        member.add_roles.assert_called_once_with(role)

    async def test_skips_bot_members(self, cog):
        """Reaction add must not assign roles to bot accounts."""
        cog.reaction_roles = {12345: {"👍": 67890}}

        member = _member(is_bot=True)
        role = MagicMock()
        cog.bot.get_guild.return_value = _guild(role, member)

        await cog.on_raw_reaction_add(_payload(12345, "👍"))

        member.add_roles.assert_not_called()

    async def test_ignores_untracked_message(self, cog):
        """Reaction add on a message not in reaction_roles must be a no-op."""
        cog.reaction_roles = {}

        await cog.on_raw_reaction_add(_payload(99999, "👍"))

        cog.bot.get_guild.assert_not_called()

    async def test_ignores_untracked_emoji(self, cog):
        """Reaction add with an emoji not in the mapping must be a no-op."""
        cog.reaction_roles = {12345: {"👍": 67890}}

        await cog.on_raw_reaction_add(_payload(12345, "❌"))

        cog.bot.get_guild.assert_not_called()

    async def test_handles_deleted_role(self, cog):
        """Reaction add must not raise if the role no longer exists in the guild."""
        cog.reaction_roles = {12345: {"👍": 67890}}

        guild = MagicMock()
        guild.get_role.return_value = None  # role was deleted
        cog.bot.get_guild.return_value = guild

        # Should complete without raising
        await cog.on_raw_reaction_add(_payload(12345, "👍"))


# ---------------------------------------------------------------------------
# on_raw_reaction_remove
# ---------------------------------------------------------------------------


class TestOnRawReactionRemove:
    async def test_removes_role_from_human_member(self, cog):
        """Reaction remove must strip the mapped role from a non-bot member."""
        cog.reaction_roles = {12345: {"👍": 67890}}

        member = _member(is_bot=False)
        role = MagicMock()
        cog.bot.get_guild.return_value = _guild(role, member)

        await cog.on_raw_reaction_remove(_payload(12345, "👍"))

        member.remove_roles.assert_called_once_with(role)

    async def test_skips_bot_members(self, cog):
        """Reaction remove must not strip roles from bot accounts."""
        cog.reaction_roles = {12345: {"👍": 67890}}

        member = _member(is_bot=True)
        role = MagicMock()
        cog.bot.get_guild.return_value = _guild(role, member)

        await cog.on_raw_reaction_remove(_payload(12345, "👍"))

        member.remove_roles.assert_not_called()

    async def test_ignores_untracked_message(self, cog):
        """Reaction remove on an untracked message must be a no-op."""
        cog.reaction_roles = {}

        await cog.on_raw_reaction_remove(_payload(99999, "👍"))

        cog.bot.get_guild.assert_not_called()

    async def test_ignores_untracked_emoji(self, cog):
        """Reaction remove with an untracked emoji must be a no-op."""
        cog.reaction_roles = {12345: {"👍": 67890}}

        await cog.on_raw_reaction_remove(_payload(12345, "❌"))

        cog.bot.get_guild.assert_not_called()

    async def test_handles_deleted_role(self, cog):
        """Reaction remove must not raise if the role no longer exists."""
        cog.reaction_roles = {12345: {"👍": 67890}}

        guild = MagicMock()
        guild.get_role.return_value = None
        cog.bot.get_guild.return_value = guild

        await cog.on_raw_reaction_remove(_payload(12345, "👍"))
