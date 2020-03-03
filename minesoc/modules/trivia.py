# trivia.py
# So many questions so little time.

import discord
import asyncio
import time

from discord.ext import commands


class Trivia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def user_check(self, user_id):
        return await self.bot.db.fetchrow("SELECT EXISTS(SELECT 1 FROM economy WHERE user_id=$1)", user_id)

    @commands.command()
    @commands.cooldown(1, 30, commands.BucketType.user)
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
                if int(message.content) == result.answers.index(result.correct) + 1:
                    check = await self.user_check(ctx.author.id)

                    if check[0]:
                        result = await self.bot.db.fetchrow("SELECT amount FROM economy WHERE user_id=$1",
                                                            ctx.author.id)
                        await self.bot.db.execute("UPDATE economy SET amount=$1 WHERE user_id=$2",
                                                  result["amount"] + 200, ctx.author.id)
                    else:
                        await self.bot.db.execute("INSERT INTO economy (user_id, amount, cd, streak, streak_time) "
                                                  "VALUES ($1, $2, $3, 0, 0)", ctx.author.id, 200, time.time())

                    await ctx.send(embed=discord.Embed(title="🎉 Correct! You earned **$200** credits!",
                                                       color=self.bot.colors.green))
                else:
                    await ctx.send(embed=discord.Embed(title=f"😔 Sorry! The answer was {result.correct}",
                                                       color=self.bot.colors.neutral))

        else:
            await ctx.error(f"Command failed! If you would like assistance, let the bot owner know: "
                            f"RESPONSE_CODE {result}")


def setup(bot):
    bot.add_cog(Trivia(bot))
