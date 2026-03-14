import discord
from discord import app_commands
from discord.ext import commands

from utils.llm_api import query_llm


class LLM(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ask", description="Ask the bot's AI a question.")
    @app_commands.describe(question="The question or prompt to ask the AI.")
    async def ask(self, interaction: discord.Interaction, question: str):
        # Acknowledge the interaction immediately to avoid timeout
        await interaction.response.defer(ephemeral=False)

        response = await query_llm(question)

        # Responses might be long, slice to Discord's 2000 character limit.
        if len(response) > 2000:
            response = response[:1996] + "..."

        await interaction.followup.send(response)


async def setup(bot: commands.Bot):
    await bot.add_cog(LLM(bot))
