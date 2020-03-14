# corona.py
# This cog should provide info to users about Novel Coronavirus (COVID-19)
import discord

from discord.ext import commands


class Corona(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def corona(self, ctx):
        async with ctx.typing():
            embed = (await self.bot.api.corona.fetch_data()).embed
            embed.title = f"{self.bot.custom_emojis.virus} COVID-19 Information"
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Corona(bot))
