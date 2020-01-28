import discord
import asyncio
import aiohttp.client
import textwrap

from discord.ext import commands
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from random import getrandbits


def binary_to_decimal(binary):
    return int(binary, 2)


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


class Spotify:
    def __init__(self):
        self.font = ImageFont.truetype("arial-unicode-ms.ttf", 16)
        self.medium_font = ImageFont.truetype("arial-unicode-ms.ttf", 18)
        self.session = aiohttp.ClientSession()

    def draw(self, name, artists, color, album_bytes: BytesIO):
        r = color[0]
        g = color[1]
        b = color[2]
        album_bytes = Image.open(album_bytes)
        size = (160, 160)
        album_bytes = album_bytes.resize(size)
        im = Image.new("RGBA", (500, 170), (r, g, b, 255))

        im_draw = ImageDraw.Draw(im)
        im_draw.rectangle((5, 5, 495, 165), fill=(5, 5, 25))
        im_draw.text((175, 30), name, font=self.medium_font, fill=(255, 255, 255, 255))

        artist_text = ", ".join(artists)
        artist_text = "\n".join(textwrap.wrap(artist_text, width=35))
        im_draw.text((175, 62), artist_text, font=self.font, fill=(255, 255, 255, 255))

        im.paste(album_bytes, (5, 5))

        buffer = BytesIO()
        im.save(buffer, "png")
        buffer.seek(0)

        return buffer

    async def fetch_cover(self, cover_url):
        async with self.session as s:
            async with s.get(f"{cover_url}?size=128") as r:
                if r.status == 200:
                    return await r.read()


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    async def binary(self, ctx):
        """Binary related commands"""
        if ctx.invoked_subcommand is None:
            await ctx.send("Invalid command.")

    @binary.command()
    async def a2b(self, ctx, *, string):
        """Convert a string to binary"""
        if isinstance(string, int):
            result = f"{int(string):08b}"
        else:
            result = " ".join(format(ord(x), "b") for x in string)

        embed = discord.Embed()
        if len(result) >= 300:
            embed.colour = self.bot.colors.red
            embed.title = "Output can't exceed 300 characters!"
            await ctx.message.add_reaction("❗")
        else:
            embed.colour = self.bot.colors.neutral
            embed.title = f"{string} ->"
            embed.description = f"**{result}**"
            await ctx.message.delete()

        async with ctx.typing():
            await asyncio.sleep(2.5)
            await ctx.message.delete
            await ctx.send(embed=embed)

    @binary.command()
    async def b2a(self, ctx, *, bin_data):
        bin_data = str(bin_data).replace(" ", "")

        str_data = ""

        for i in range(0, len(bin_data), 7):
            temp_data = bin_data[i:i + 7]
            decimal_data = binary_to_decimal(temp_data)
            str_data = str_data + chr(decimal_data)

        embed = discord.Embed()
        if len(str_data) >= 300:
            embed.colour = self.bot.colors.red
            embed.title = "Output can't exceed 300 characters!"
            await ctx.message.add_reaction("❗")
        else:
            embed.colour = self.bot.colors.neutral
            embed.title = f"{bin_data} ->"
            embed.description = f"**{str_data}**"
            await ctx.message.add_reaction("👌")

        async with ctx.typing():
            await asyncio.sleep(2.5)
            await ctx.message.delete
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
        if ctx.invoked_subcommand is None:
            await ctx.send("Invalid command.")

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
    async def spotify(self, ctx, user: discord.Member = None):
        user = ctx.author if not user else user
        if user.bot:
            return

        for activity in user.activities:
            if isinstance(activity, discord.Spotify):
                spotify_card = Spotify()

                album_bytes = await spotify_card.fetch_cover(activity.album_cover_url)
                color = activity.color.to_rgb()

                buffer = spotify_card.draw(activity.title, activity.artists, color, BytesIO(album_bytes))

                await ctx.send(file=discord.File(fp=buffer, filename="spotify.png"))

    @commands.command()
    async def robohash(self, ctx, *, query: str = None):
        if query is None:
            query = getrandbits(128)
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://robohash.org/{query}") as response:
                robo_bytes = await response.read()

        async with ctx.typing():
            buffer = BytesIO(robo_bytes)
            await ctx.send(file=discord.File(fp=buffer, filename="robohash.png"))


def setup(bot):
    bot.add_cog(Fun(bot))
