import discord
import aiohttp.client

from discord.ext import commands


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def binary(self, ctx, *item):
        res = list()
        for i in item:
            for j in i:
                res.append("".join(format(x, "b") for x in bytearray(j, encoding="utf-8")))

        embed = discord.Embed()
        async with ctx.typing():
            if len("".join(res)) >= 300:
                embed.colour = self.bot.colors.red
                embed.title = "Output can't exceed 300 characters!"
                await ctx.message.add_reaction("❗")
            else:
                embed.colour = self.bot.colors.neutral
                embed.title = f"{''.join(item)} ->"
                embed.description = f"**{''.join(res)}**"
                await ctx.message.add_reaction("👌")

            await ctx.send(embed=embed)

    @commands.command()
    async def cat(self, ctx):
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get("https://aws.random.cat/meow") as r:
                    data = await r.json()

            embed = discord.Embed()
            embed.set_image(url=data["file"])
            await ctx.send(embed=embed)

    @commands.command()
    async def dog(self, ctx, breed: str = None, sub_breed: str = None):
        async with ctx.typing():
            if not breed:
                url = "https://dog.ceo/api/breeds/image/random"
            elif not sub_breed:
                url = f"https://dog.ceo/api/breed/{breed}/images/random"
            else:
                url = f"https://dog.ceo/api/breed/{breed}/{sub_breed}/images/random"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    data = await r.json()

            embed = discord.Embed()
            if data["status"] == "success":
                embed.set_image(url=data["message"])
            else:
                embed.colour = self.bot.colors.red
                embed.title = data["message"]
            await ctx.send(embed=embed)

    @commands.group(aliases=["da", "devart"])
    async def deviantart(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Invalid command.")

    @deviantart.command()
    async def tag(self, ctx, tag):
        async with ctx.typing():
            await ctx.send(embed=(await self.bot.api.deviantart.browse_tags(tag)).embed)

    @deviantart.command()
    async def popular(self, ctx, query: str = None, category: str = None):
        async with ctx.typing():
            await ctx.send(embed=(await self.bot.api.deviantart.browse_popular(query, category)).embed)


def setup(bot):
    bot.add_cog(Fun(bot))
