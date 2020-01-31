import discord
import asyncio
import aiohttp.client

from discord.ext import commands
from io import BytesIO
from random import getrandbits, choice


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
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @binary.command()
    async def a2b(self, ctx, *, string):
        """Convert a string to binary"""
        result = " ".join(str(i) for i in string2bits(string))

        message = ctx.message
        embed = discord.Embed()
        error = False
        if len(result) >= 300:
            embed.colour = self.bot.colors.red
            embed.title = "Output can't exceed 300 characters!"
            await ctx.message.add_reaction("❗")
            error = True
        else:
            embed.colour = self.bot.colors.neutral
            embed.title = result
            await ctx.message.add_reaction("👌")

        bot_msg = await ctx.send(embed=embed)

        if error:
            await asyncio.sleep(5)
            await bot_msg.delete()
            await message.delete()

    @binary.command()
    async def b2a(self, ctx, *bin_data):
        message = ctx.message
        embed = discord.Embed()
        error = False
        try:
            bin_data = [i for i in bin_data]
            result = bits2string(bin_data)
            result = "".join(str(i) for i in result)
            if len(result) >= 300:
                embed.colour = self.bot.colors.red
                embed.title = "Output can't exceed 300 characters!"
                await ctx.message.add_reaction("❗")
                error = True
            else:
                embed.colour = self.bot.colors.neutral
                embed.title = result
                await ctx.message.add_reaction("👌")
        except ValueError:
            embed = discord.Embed()
            embed.colour = self.bot.colors.red
            embed.title = "Input must be binary!"
            await ctx.message.add_reaction("❗")
            error = True
        finally:
            bot_msg = await ctx.send(embed=embed)

            if error:
                await asyncio.sleep(5)
                await bot_msg.delete()
                await message.delete()

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
        if ctx.invoked_subcommand is None:
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

    @commands.group(aliases=["robo", "rh"])
    async def robohash(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @robohash.command()
    async def robot(self, ctx, *, query: str = None):
        query = query or getrandbits(128)
        async with ctx.typing(), aiohttp.ClientSession() as session:
            async with session.get(f"https://robohash.org/{query}") as response:
                robo_bytes = await response.read()

        buffer = BytesIO(robo_bytes)
        await ctx.send(file=discord.File(fp=buffer, filename=f"{query}.png"))

    @robohash.command()
    async def monster(self, ctx, *, query: str = None):
        query = query or getrandbits(128)
        async with ctx.typing(), aiohttp.ClientSession() as session:
            async with session.get(f"https://robohash.org/{query}?set=set2") as response:
                robo_bytes = await response.read()

        buffer = BytesIO(robo_bytes)
        await ctx.send(file=discord.File(fp=buffer, filename=f"{query}.png"))

    @robohash.command()
    async def robohead(self, ctx, *, query: str = None):
        query = query or getrandbits(128)
        async with ctx.typing(), aiohttp.ClientSession() as session:
            async with session.get(f"https://robohash.org/{query}?set=set3") as response:
                robo_bytes = await response.read()

        buffer = BytesIO(robo_bytes)
        await ctx.send(file=discord.File(fp=buffer, filename=f"{query}.png"))

    @robohash.command()
    async def kitten(self, ctx, *, query: str = None):
        query = query or getrandbits(128)
        async with ctx.typing(), aiohttp.ClientSession() as session:
            async with session.get(f"https://robohash.org/{query}?set=set4") as response:
                robo_bytes = await response.read()

        buffer = BytesIO(robo_bytes)
        await ctx.send(file=discord.File(fp=buffer, filename=f"{query}.png"))

    @robohash.command()
    async def human(self, ctx, *, query: str = None):
        query = query or getrandbits(128)
        async with ctx.typing(), aiohttp.ClientSession() as session:
            async with session.get(f"https://robohash.org/{query}?set=set5") as response:
                robo_bytes = await response.read()

        buffer = BytesIO(robo_bytes)
        await ctx.send(file=discord.File(fp=buffer, filename=f"{query}.png"))

    @commands.command(aliases=["choice"])
    async def choose(self, ctx, *choices):
        choices = [str(i) for i in choices]

        await ctx.send(f"I choose: {choice(choices)}")


def setup(bot):
    bot.add_cog(Fun(bot))
