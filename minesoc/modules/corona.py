# corona.py
# This cog should provide info to users about Novel Coronavirus (COVID-19)
import discord

from discord.ext import commands


class Corona(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    async def corona(self, ctx):
        if ctx.invoked_subcommands is None:
            async with ctx.typing():
                await ctx.send(embed=(await self.bot.api.corona.fetch_data(data="all")).embed)

    @corona.command(name="recovered")
    async def corona_recovered(self, ctx, country):
        async with ctx.typing():
            await ctx.send(embed=(await self.bot.api.corona.fetch_data(data="recovered", country=country)).embed)

    @corona.command(name="deaths")
    async def corona_deaths(self, ctx, country):
        async with ctx.typing():
            await ctx.send(embed=(await self.bot.api.corona.fetch_data(data="deaths", country=country)).embed)

    @corona.command(name="confirmed")
    async def corona_confirmed(self, ctx, country):
        async with ctx.typing():
            await ctx.send(embed=(await self.bot.api.corona.fetch_data(data="confirmed", country=country)).embed)


def setup(bot):
    bot.add_cog(Corona(bot))
