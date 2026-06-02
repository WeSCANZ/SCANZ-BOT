import sys
import os
import pytest
import discord
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
import pytz

# Add project root to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cogs.general import General

@pytest.fixture
def bot():
    return MagicMock()

@pytest.fixture
def cog(bot):
    return General(bot)

@pytest.mark.asyncio
async def test_hi_command(cog):
    """/hi command should greeting with standard SC elements."""
    interaction = MagicMock(spec=discord.Interaction)
    interaction.user.display_name = "Vengefulpineapple"
    interaction.response.send_message = AsyncMock()

    await cog.hi.callback(cog, interaction)

    interaction.response.send_message.assert_called_once()
    called_arg = interaction.response.send_message.call_args[0][0]
    
    assert "Vengefulpineapple" in called_arg
    assert any(term in called_arg for term in ["Greetings", "Hello there", "Top of the morning", "o7", "Aha!"])

@pytest.mark.asyncio
async def test_time_command(cog):
    """/time command should show dynamic times for ICT, AWST, AET, NZT by default."""
    interaction = MagicMock(spec=discord.Interaction)
    interaction.response.send_message = AsyncMock()

    await cog.time.callback(cog, interaction)

    interaction.response.send_message.assert_called_once()
    embed = interaction.response.send_message.call_args[1].get("embed")
    assert embed is not None
    assert embed.title == "🕐 SCANZ Global Times"
    assert "Your local time:" in embed.description

    fields = {f.name: f.value for f in embed.fields}
    assert "🇹🇭 Indochina (ICT)" in fields
    assert "🇦🇺 Perth (AWST)" in fields
    assert "🇦🇺 Melbourne/Sydney (AET)" in fields
    assert "🇳🇿 New Zealand (NZT)" in fields
    assert "📋 Copyable Timestamps" in fields

    # Each zone field should contain a dynamic Discord timestamp tag
    for zone_name in ["🇹🇭 Indochina (ICT)", "🇦🇺 Perth (AWST)", "🇦🇺 Melbourne/Sydney (AET)", "🇳🇿 New Zealand (NZT)"]:
        assert "<t:" in fields[zone_name]

@pytest.mark.asyncio
async def test_time_command_with_conversion(cog):
    """/time command should parse valid times and display timezone equivalents."""
    interaction = MagicMock(spec=discord.Interaction)
    interaction.response.send_message = AsyncMock()

    await cog.time.callback(cog, interaction, time_input="10:00 PM", timezone="AET")

    interaction.response.send_message.assert_called_once()
    embed = interaction.response.send_message.call_args[1].get("embed")
    assert embed is not None
    assert embed.title == "🕐 SCANZ Time Converter"
    assert "10:00 PM" in embed.description

    fields = {f.name: f.value for f in embed.fields}
    # Check that AET field shows 10:00 PM in the static italic line
    assert "10:00 PM" in fields["🇦🇺 Melbourne/Sydney (AET)"]
    # Check ICT shows 07:00 PM (AET is UTC+10, ICT is UTC+7)
    assert "07:00 PM" in fields["🇹🇭 Indochina (ICT)"]

@pytest.mark.asyncio
async def test_time_command_invalid_input(cog):
    """/time command should respond with an error message for invalid inputs."""
    interaction = MagicMock(spec=discord.Interaction)
    interaction.response.send_message = AsyncMock()

    await cog.time.callback(cog, interaction, time_input="not-a-time", timezone="AET")

    interaction.response.send_message.assert_called_once()
    called_arg = interaction.response.send_message.call_args[0][0]
    assert "❌ **Invalid Time Format:**" in called_arg
    assert interaction.response.send_message.call_args[1].get("ephemeral") is True

@pytest.mark.asyncio
async def test_latency_command(cog):
    """/latency command should report telemetry latency."""
    cog.bot.latency = 0.042  # 42ms
    interaction = MagicMock(spec=discord.Interaction)
    interaction.response.send_message = AsyncMock()

    await cog.latency.callback(cog, interaction)

    interaction.response.send_message.assert_called_once()
    embed = interaction.response.send_message.call_args[1].get("embed")
    assert embed is not None
    assert embed.title == "🏓 Pong!"
    assert "`42ms`" in embed.description
