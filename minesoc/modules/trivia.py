# trivia.py
# So many questions so little time.

import discord
import asyncio

from discord.ext import commands


class Trivia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def trivia(self, ctx):
        result = await self.bot.api.trivia.get_trivia()

        if isinstance(result.embed, discord.Embed):
            await ctx.send(embed=result.embed)

            responses = [i + 1 for i in range(len(result.answers))]

            def check(author):
                def inner_check(msg):
                    if msg.author != author:
                        return False
                    if int(msg.content) in responses:
                        return True
                    else:
                        return False

                return inner_check

            try:
                message = await self.bot.wait_for("message", check=check(ctx.author), timeout=30)
            except asyncio.TimeoutError:
                await ctx.send(embed=discord.Embed(title="❗ You took too long!", color=self.bot.colors.red))
            else:
                if int(message.content) == result.answers.index(result.correct_answer) + 1:
                    await ctx.send(embed=discord.Embed(title="Correct!", color=self.bot.colors.green))
                else:
                    await ctx.send(embed=discord.Embed(title="Incorrect!", color=self.bot.colors.neutral))

        else:
            await ctx.error(f"Command failed! Notify the owner this was due to: RESPONSE_CODE {result}")


def setup(bot):
    bot.add_cog(Trivia(bot))
