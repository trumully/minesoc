import discord
import asyncio
import aiohttp.client

from discord.ext import commands
from io import BytesIO
from random import getrandbits


def string2bits(s=''):
    return [bin(ord(x))[2:].zfill(8) for x in s]


def bits2string(b=None):
    return ''.join([chr(int(x, 2)) for x in b])


def measure_time(start, end):
    duration = int(end - start)
    return seconds_to_ms(duration)


def seconds_to_ms(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return "%02d:%02d" % (minutes, seconds)


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    async def binary(self, ctx):
        """Binary related commands"""
        await ctx.send_help(ctx.command)

    @binary.command()
    async def a2b(self, ctx, *, string):
        """Convert a string to binary"""
        result = " ".join(str(i) for i in string2bits(string))

        embed = discord.Embed()
        if len(result) >= 300:
            embed.colour = self.bot.colors.red
            embed.title = "Output can't exceed 300 characters!"
            await ctx.message.add_reaction("❗")
        else:
            embed.colour = self.bot.colors.neutral
            embed.title = result
            await ctx.message.add_reaction("👌")

        await ctx.send(embed=embed)

    @binary.command()
    async def b2a(self, ctx, *bin_data):
        bin_data = [i for i in bin_data]
        result = bits2string(bin_data)
        result = "".join(str(i) for i in result)

        embed = discord.Embed()
        if len(bin_data) >= 300:
            embed.colour = self.bot.colors.red
            embed.title = "Output can't exceed 300 characters!"
            await ctx.message.add_reaction("❗")
        else:
            embed.colour = self.bot.colors.neutral
            embed.title = result
            await ctx.message.add_reaction("👌")

        await ctx.send(embed=embed)

    @commands.command()
    async def cat(self, ctx):
        """Returns a random image of a cat."""
        message = await ctx.send(
            embed=discord.Embed(color=discord.Color.greyple(), title=f"{self.bot.emojis.typing} **Searching ...**"
                                ))
        async with ctx.typing():
            await asyncio.sleep(2.5)
            await message.delete()
            await ctx.send(embed=(await self.bot.api.animal.fetch_cat()).embed)

    @commands.command()
    async def dog(self, ctx, breed: str = None, sub_breed: str = None):
        """Returns a random image of a dog."""
        message = await ctx.send(
            embed=discord.Embed(color=discord.Color.greyple(), title=f"{self.bot.emojis.typing} **Searching ...**"
                                ))
        async with ctx.typing():
            await asyncio.sleep(2.5)
            await message.delete()
            await ctx.send(embed=(await self.bot.api.animal.fetch_dog(breed, sub_breed)).embed)

    @commands.group(aliases=["da", "devart"])
    async def deviantart(self, ctx):
        """Offers options to browse DeviantArt."""
        await ctx.send_help(ctx.command)

    @deviantart.command()
    async def tag(self, ctx, tag):
        """Get a Deviant by tag."""
        message = await ctx.send(
            embed=discord.Embed(color=discord.Color.greyple(), title=f"{self.bot.emojis.typing} **Searching ...**"
                                ))
        async with ctx.typing():
            await asyncio.sleep(2.5)
            await message.delete()
            await ctx.send(embed=(await self.bot.api.deviantart.browse_tags(tag)).embed)

    @deviantart.command()
    async def popular(self, ctx, query: str = None, category: str = None):
        """Get a Deviant by popularity."""
        message = await ctx.send(
            embed=discord.Embed(color=discord.Color.greyple(), title=f"{self.bot.emojis.typing} **Searching ...**"
                                ))
        async with ctx.typing():
            await asyncio.sleep(2.5)
            await message.delete()
            await ctx.send(embed=(await self.bot.api.deviantart.browse_popular(query, category)).embed)

    @commands.command()
    async def robohash(self, ctx, *, query: str = None):
        query = query or getrandbits(128)
        async with ctx.typing(), aiohttp.ClientSession() as session:
            async with session.get(f"https://robohash.org/{query}") as response:
                robo_bytes = await response.read()

        buffer = BytesIO(robo_bytes)
        await ctx.send(file=discord.File(fp=buffer, filename=f"{query}.png"))


def setup(bot):
    bot.add_cog(Fun(bot))
