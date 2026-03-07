"""Shared app_commands checks for SCANZ-BOT."""

import discord
from discord import app_commands


async def has_staff_or_admin(interaction: discord.Interaction) -> bool:
    """
    Require the user to have the configured staff role OR Administrator permission.
    Used for commands that should be available to a custom role (e.g. Custodian)
    as well as full server admins.
    If no staff role is configured, only Administrator is allowed (backward compatible).
    """
    if not interaction.guild or not interaction.user:
        return False
    member = interaction.user
    if not isinstance(member, discord.Member):
        return False
    if member.guild_permissions.administrator:
        return True
    ver_cog = interaction.client.get_cog("RSIVerification")
    if ver_cog and hasattr(ver_cog, "_get_config"):
        role_id_str = ver_cog._get_config("staff_role_id")
        if role_id_str:
            role = interaction.guild.get_role(int(role_id_str))
            if role and role in member.roles:
                return True
    return False
