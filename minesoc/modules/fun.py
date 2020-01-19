import discord

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


def setup(bot):
    bot.add_cog(Fun(bot))
