import asyncio
import string
from random import choice, choices, randint

import discord
from discord.ext import commands

_8ball = ["It is certain.", "It is decidedly so.", "Without a doubt.", "Yes - definitely.", "You may rely on it.",
          "As I see it, yes.", "Most likely.", "Outlook good.", "Yes.", "Signs point to yes", "Reply hazy, try again.",
          "Ask again later.", "Better not tell you now.", "Cannot predict now.", "Concentrate and ask again",
          "Don't count on it.", "My reply is no.", "My sources say no.", "Outlook not so good.", "Very doubtful"]


def string2bits(s=''):
    return [bin(ord(x))[2:].zfill(8) for x in s]


def bits2string(b=None):
    return ''.join([chr(int(x, 2)) for x in b])


def robohash(query, set_num, author):
    embed = discord.Embed(color=discord.Color.blue())
    embed.set_image(url=f"https://robohash.org/{query}.png?set=set{set_num}")
    embed.set_footer(text=f"Requested by {author.name} | Provided by robohash.org", icon_url=author.avatar_url)

    return embed


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    async def binary(self, ctx):
        """Binary related commands"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @binary.command()
    async def a2b(self, ctx, *, ascii_string):
        """Convert a string to binary"""
        result = " ".join(str(i) for i in string2bits(ascii_string))

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
            embed=discord.Embed(color=discord.Color.greyple(),
                                title=f"{self.bot.custom_emojis.typing} **Searching ...**"
                                ))
        async with ctx.typing():
            await asyncio.sleep(2.5)
            await message.delete()
            await ctx.send(embed=(await self.bot.api.animal.fetch_cat()).embed)

    @commands.command()
    async def dog(self, ctx, breed: str = None, sub_breed: str = None):
        """Returns a random image of a dog."""
        message = await ctx.send(
            embed=discord.Embed(color=discord.Color.greyple(),
                                title=f"{self.bot.custom_emojis.typing} **Searching ...**"
                                ))
        async with ctx.typing():
            await asyncio.sleep(2.5)
            await message.delete()
            await ctx.send(embed=(await self.bot.api.animal.fetch_dog(breed, sub_breed)).embed)

    @commands.group(aliases=["robo", "rh"])
    async def robohash(self, ctx):
        """Get randomly generated images from robohash.org"""
        if ctx.invoked_subcommand is None:
            query = ''.join(choices(string.ascii_uppercase + string.digits, k=3))
            await ctx.send(embed=robohash(query, randint(1, 5), ctx.author))

    @robohash.command()
    async def robot(self, ctx, *, query: str = None):
        """Get a randomly generated robot from robohash.org"""
        query = query or ''.join(choices(string.ascii_uppercase + string.digits, k=3))
        await ctx.send(embed=robohash(query, 1, ctx.author))

    @robohash.command()
    async def monster(self, ctx, *, query: str = None):
        """Get a randomly generated monster from robohash.org"""
        query = query or ''.join(choices(string.ascii_uppercase + string.digits, k=3))
        await ctx.send(embed=robohash(query, 2, ctx.author))

    @robohash.command()
    async def robohead(self, ctx, *, query: str = None):
        """Get a randomly generated robohead from robohash.org"""
        query = query or ''.join(choices(string.ascii_uppercase + string.digits, k=3))
        await ctx.send(embed=robohash(query, 3, ctx.author))

    @robohash.command()
    async def kitten(self, ctx, *, query: str = None):
        """Get a randomly generated kitten from robohash.org"""
        query = query or ''.join(choices(string.ascii_uppercase + string.digits, k=3))
        await ctx.send(embed=robohash(query, 4, ctx.author))

    @robohash.command()
    async def human(self, ctx, *, query: str = None):
        """Get a randomly generated human from robohash.org"""
        query = query or ''.join(choices(string.ascii_uppercase + string.digits, k=3))
        await ctx.send(embed=robohash(query, 5, ctx.author))

    @commands.command(aliases=["choice"])
    async def choose(self, ctx, *options):
        """Having trouble making a decision? I'll make it for you!"""
        await ctx.send(f"I choose: {choice(options)}")

    @commands.command(name="8ball")
    async def _8ball(self, ctx, *, query):
        """"""
        await ctx.send(f"> {query}\n🎱 {choice(_8ball)}")

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def curse(self, ctx, member: discord.Member = None):
        message = f"**{str(ctx.author)}** cursed **{str(member)}**!" if member else f"**{str(ctx.author)}** cursed themself?"
        await ctx.send(message, file=discord.File("videos/curse.mp4", filename="curse.mp4"))


def setup(bot):
    bot.add_cog(Fun(bot))
