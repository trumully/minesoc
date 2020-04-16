# covid.py
# This cog should provide info to users about Novel Coronavirus (COVID-19)
import discord

from discord.ext import commands


class Covid(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    async def covid(self, ctx):
        if ctx.invoked_subcommand is None:
            async with ctx.typing():
                await ctx.send(embed=(await self.bot.api.corona.fetch_latest()).embed)

    @covid.command(name="country")
    async def corona_recovered(self, ctx, *, country):
        async with ctx.typing():
            await ctx.send(embed=(await self.bot.api.corona.fetch_country(q=country)).embed)


def setup(bot):
    bot.add_cog(Covid(bot))
