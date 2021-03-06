# status.py
# This extension contains commands relating to Minecraft queries
import asyncio
from datetime import datetime

import aiohttp.client
import discord
from discord.ext import commands


class Minecraft(commands.Cog, name="Minecraft"):
    """Minecraft related commands"""

    def __init__(self, bot):
        self.bot = bot

    # Commands
    @commands.command(name="query", help="Queries a MC server. Only works if server has enable-query set to true")
    @commands.cooldown(1, 10, type=commands.BucketType.user)
    async def query(self, ctx, address: str):
        """
        Queries a specified Minecraft server gaining detailed information of the server.
        """
        msg = await ctx.send(embed=discord.Embed(title=f"{self.bot.custom_emojis.typing} Querying {address}",
                                                 color=self.bot.colors.neutral))

        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://eu.mc-api.net/v3/server/ping/{address}") as r:
                    try:
                        res = await r.json()
                    except:
                        embed = discord.Embed(title="An unexpected error has occurred.", colour=self.bot.colors.red)
                    finally:
                        await session.close()
            online = res["online"]
            if online:
                favicon = res["favicon"]
                try:
                    motd = res["description"]["text"]
                except TypeError:
                    motd = res["description"]
                players = f"{res['players']['online']}/{res['players']['max']}"
                version = res["version"]["name"]
                timestamp = datetime.strptime(res["fetch"], "%Y-%m-%dT%H:%M:%S.%fZ")
                embed = discord.Embed(title=address, colour=self.bot.colors.green,
                                      description=motd, timestamp=timestamp)
                embed.set_footer(icon_url=ctx.author.avatar_url, text=ctx.author.name)
                embed.set_thumbnail(url=favicon)
                embed.add_field(name="Version", value=f"{self.bot.custom_emojis.minecraft} {version}")
                embed.add_field(name="Players", value=players)
            else:
                embed = discord.Embed(title=f"{address} may be offline or invalid", colour=self.bot.colors.neutral)

        await asyncio.sleep(2.5)
        await msg.delete()
        await ctx.send(embed=embed)

    @query.error
    async def query_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Please enter a server address.")
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.message.add_reaction("🕒")


def setup(bot):
    bot.add_cog(Minecraft(bot))
