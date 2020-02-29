# economy.py
# Money! Money! Money!
import time
import random

from discord.ext import commands
from libneko.aggregates import Proxy

COOLDOWN = 120  # 2 minutes
STREAK_TIMER = 3600 * 28  # 28 hours


class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.credit_gain = Proxy(min=10, max=50)
        self.daily_gain = 200

        self.bot.loop.create_task(self.economy_table())

    def gen_currency(self, proxy):
        return random.randint(proxy.min, proxy.max)

    async def economy_table(self):
        await self.bot.wait_until_ready()

        await self.bot.db.execute("CREATE TABLE IF NOT EXISTS economy(user_id BIGINT, amount BIGINT, cd REAL, streak BIGINT, streak_time REAL)")

    async def user_check(self, user_id):
        return await self.bot.db.fetchrow("SELECT EXISTS(SELECT 1 FROM economy WHERE user_id=$1)", user_id)

    @commands.Cog.listener()
    async def on_message(self, message):
        author = message.author.id
        ctx = await self.bot.get_context(message)

        if message.author.bot or ctx.valid:
            return

        check = await self.user_check(author)

        gain = self.gen_currency(self.credit_gain)

        if check[0]:
            result = await self.bot.db.fetchrow("SELECT amount, cd FROM economy WHERE user_id=$1", author)
            if time.time() - result["cd"] >= COOLDOWN:
                await self.bot.db.execute("UPDATE economy SET amount=$1, cd=$2 WHERE user_id=$3",
                                          result["amount"] + gain, time.time(), author)
        else:
            await self.bot.db.execute("INSERT INTO economy (user_id, amount, cd, streak, streak_time) "
                                      "VALUES ($1, $2, $3, 0, 0)", author, gain, time.time())

    @commands.command()
    async def balance(self, ctx):
        check = await self.user_check(ctx.author.id)

        if check[0]:
            result = await self.bot.db.fetchrow("SELECT amount FROM economy WHERE user_id=$1", ctx.author.id)
            await ctx.send(f"💎 | You have **${result['amount']}** credits.")
        else:
            await ctx.send("**You haven't earned any credits yet!**")

    @commands.command()
    @commands.cooldown(1, 3600*24, type=commands.BucketType.user)  # 24 hour cooldown
    async def daily(self, ctx):
        author = ctx.author.id

        check = await self.user_check(author)

        if check[0]:
            result = await self.bot.db.fetchrow("SELECT amount, streak, streak_time FROM economy WHERE user_id=$1",
                                                author)

            streak = result["streak"] + 1
            streak_bonus = 0

            if time.time() - result["streak_time"] >= STREAK_TIMER:
                streak = 0

            if streak % 5 == 0:
                streak_bonus = self.gen_currency(self.credit_gain) * 2

            net_gain = result["amount"] + self.daily_gain + streak_bonus

            await self.bot.db.execute("UPDATE economy SET amount=$1, streak=$2, streak_time=$3 WHERE user_id=$4",
                                      net_gain, streak, time.time(), author)

            msg = f"💸 | **You got ${self.daily_gain} credits!\n\nStreak: {streak}**"

            if streak_bonus > 0:
                msg += f"\n\n**You completed a streak and earned an extra ${streak_bonus} credits ({net_gain} total)!**"

        else:
            await self.bot.db.execute("INSERT INTO economy (user_id, amount, cd, streak, streak_time) "
                                      "VALUES ($1, $2, $3, 1, $4)", author, self.daily_gain, time.time(), time.time())

            msg = f"💸 | **You got ${self.daily_gain} credits!\n\nStreak: 1**"

        await ctx.send(msg)


def setup(bot):
    bot.add_cog(Economy(bot))
