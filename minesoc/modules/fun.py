import discord
import asyncio

from discord.ext import commands


def binary_to_decimal(binary):
    return int(binary, 2)


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
            await ctx.message.add_reaction("👌")

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


def setup(bot):
    bot.add_cog(Fun(bot))
