
import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock
import discord

# Mocking the bot class and dependencies
class MockBot:
    def __init__(self):
        self.admin_log_channel_id = 123456789
        self.get_channel = MagicMock()
        
    async def log_admin_action(self, embed: discord.Embed):
        """Mock implementation of the log_admin_action method from main.py"""
        if not self.admin_log_channel_id:
            return

        channel = self.get_channel(self.admin_log_channel_id)
        if not channel:
            print(f"Admin log channel {self.admin_log_channel_id} not found.")
            return

        try:
            await channel.send(embed=embed)
            print(f"Logged action to {channel.name}: {embed.title}")
        except Exception as e:
            print(f"Failed to send admin log: {e}")

class TestAdminLogging(unittest.IsolatedAsyncioTestCase):
    async def test_log_admin_action_success(self):
        bot = MockBot()
        mock_channel = AsyncMock(spec=discord.TextChannel)
        mock_channel.name = "admin-notifications"
        bot.get_channel.return_value = mock_channel
        
        embed = discord.Embed(title="Test Action", description="This is a test")
        await bot.log_admin_action(embed)
        
        mock_channel.send.assert_called_once_with(embed=embed)

    async def test_log_admin_action_no_channel(self):
        bot = MockBot()
        bot.get_channel.return_value = None
        
        embed = discord.Embed(title="Test Action", description="This is a test")
        await bot.log_admin_action(embed)
        # Should not raise exception, just print warning

if __name__ == "__main__":
    unittest.main()
