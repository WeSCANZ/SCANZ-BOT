import discord
from discord.ext import commands
import random
import re

class MentionResponder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Keyword to response mapping
        self.keyword_responses = {
            r'\b(website|link)\b': "You can find everything you need on our official website: https://wescanz.com",
            r'\b(discord|invite)\b': "Looking to invite someone? Here's our permanent Discord link: https://discord.gg/3atj8pjhFH",
            r'\b(org|rsi)\b': "Check out our official RSI Org page here: https://robertsspaceindustries.com/orgs/SCANZ",
            r'\b(status|server)\b': "Curious if the servers are on fire? Use the `!status` command to find out!",
            r'\b(help|commands)\b': "I have a lot of tools! Try typing `/scanz_commands` to see what I can do.",
            r'\b(hello|hi|hey|greetings)\b': "Greetings, starfarer! Hope your journeys in the verse have been profitable."
        }
        
        # Fallback responses if no keyword is found
        self.fallback_responses = [
            "I'm currently recalibrating the quantum drive, what do you need?",
            "Did someone say Jump Point? No? Okay, never mind.",
            "I'm a bot of few words unless you ask me about the `website`, `discord`, or `help`.",
            "Please stand by, I am currently negotiating a very lucrative salvage claim.",
            "Scanning... no hostile contacts detected. Proceed.",
            "If you're looking for a group, don't forget you can use the `/post` command in the LFG channels!"
        ]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bots and webhooks (prevents infinite loops)
        if message.author.bot or message.webhook_id:
            return

        # Check if the bot was explicitly mentioned
        if self.bot.user in message.mentions:
            content_lower = message.content.lower()
            response = None
            
            # 1. Check for specific keywords
            for pattern, reply in self.keyword_responses.items():
                if re.search(pattern, content_lower):
                    response = reply
                    break # Stop at the first matched keyword
            
            # 2. Fallback to a random witty response if no keyword matches
            if not response:
                response = random.choice(self.fallback_responses)
                
            # Reply securely preventing everyone/here pings
            await message.reply(
                content=response,
                allowed_mentions=discord.AllowedMentions(replied_user=True, everyone=False, roles=False)
            )

async def setup(bot):
    await bot.add_cog(MentionResponder(bot))
