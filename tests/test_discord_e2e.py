import asyncio
import os
import pytest
import discord
from dotenv import load_dotenv

# Run: PYTHONPATH=. /mnt/vault/Projects/SCANZ-BOT/.venv/bin/pytest tests/test_discord_e2e.py -v

load_dotenv()
load_dotenv("/root/.hermes/.env")

# We use VengeBot's token to monitor and audit interactions
BOT_TOKEN=os.getenv("DISCORD_BOT_TOKEN")
SAM_USER_ID = 516465763826008084 # Your ID Vengefulpineapple

@pytest.mark.asyncio
async def test_discord_e2e_scanz_latency():
    """Audits Sam triggering SCANZ-BOT's `/latency` command."""
    assert BOT_TOKEN is not None, "DISCORD_BOT_TOKEN missing in .env"
    
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    
    client = discord.Client(intents=intents)
    ready_event = asyncio.Event()
    message_received = asyncio.Event()
    received_embed = None

    @client.event
    async def on_ready():
        ready_event.set()

    @client.event
    async def on_message(message):
        # Monitor for SCANZ-BOT's embed reply reacting to Sam's trigger.
        # SCANZ-BOT's latency sends an embed titled '🏓 Pong!'
        if message.author.bot and message.embeds:
            for embed in message.embeds:
                if "Pong!" in str(embed.title):
                    nonlocal received_embed
                    received_embed = embed
                    message_received.set()

    async def run_test():
        assert BOT_TOKEN is not None, "DISCORD_BOT_TOKEN missing in env"
        await client.login(BOT_TOKEN)
        bot_task = asyncio.create_task(client.connect())
        
        await ready_event.wait()
        
        # Locate '#bot-testing' channel
        test_channel = None
        for guild in client.guilds:
            for channel in guild.text_channels:
                if channel.name == "bot-testing":
                    test_channel = channel
                    break
        
        assert test_channel is not None, "Could not locate #bot-testing channel!"
        
        print("\n📥 [VengeBot Auditor] Waiting for Sam to run `/latency` on Discord...")
        
        # Wait up to 30 seconds for you to trigger it on Discord
        try:
            await asyncio.wait_for(message_received.wait(), timeout=30.0)
        finally:
            await client.close()
            await bot_task

    await run_test()
    
    assert received_embed is not None, "Timeout: Did not detect SCANZ-BOT's 'Pong!' response!"
    assert "WebSocket Latency" in received_embed.description
    print("\n✅ Assertion Passed: Latency command returns robust websocket telemetry!")


@pytest.mark.asyncio
async def test_discord_e2e_scanz_hi():
    """Audits Sam triggering SCANZ-BOT's `/hi` command."""
    assert BOT_TOKEN is not None, "DISCORD_BOT_TOKEN missing in .env"
    
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    
    client = discord.Client(intents=intents)
    ready_event = asyncio.Event()
    message_received = asyncio.Event()
    received_message = None

    @client.event
    async def on_ready():
        ready_event.set()

    @client.event
    async def on_message(message):
        # SCANZ-BOT replies to `/hi` with standard text greetings matching Star Citizen themes
        if message.author.bot and not message.embeds:
            content = message.content
            # Check for known greeting responses in cogs/general.py
            if any(term in content for term in ["Greetings", "Hello there", "Top of the morning", "o7", "Aha!"]):
                nonlocal received_message
                received_message = content
                message_received.set()

    async def run_test():
        assert BOT_TOKEN is not None, "DISCORD_BOT_TOKEN missing in env"
        await client.login(BOT_TOKEN)
        bot_task = asyncio.create_task(client.connect())
        await ready_event.wait()
        
        print("\n📥 [VengeBot Auditor] Waiting for Sam to run `/hi` on Discord...")
        
        try:
            await asyncio.wait_for(message_received.wait(), timeout=30.0)
        finally:
            await client.close()
            await bot_task

    await run_test()
    
    assert received_message is not None, "Timeout: Did not detect SCANZ-BOT's greeting response!"
    assert any(term in received_message for term in ["Greetings", "Hello there", "Top of the morning", "o7", "Aha!"])
    print(f"\n✅ Assertion Passed: Bot greeted Sam with standard SC theme: '{received_message}'")
