# economy.py
# Money! Money! Money!
import time
import random

from discord.ext import commands
from libneko.aggregates import Proxy

COOLDOWN = 120  # seconds


class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.credit_gain = Proxy(min=10, max=50)

        self.bot.loop.create_task(self.economy_table())

    def gen_currency(self):
        return random.randint(self.credit_gain.min, self.credit_gain.max)

    async def economy_table(self):
        await self.bot.wait_until_ready()
        await self.bot.db.execute("CREATE TABLE IF NOT EXISTS economy(user_id BIGINT, amount BIGINT, cd REAL)")

    async def user_check(self, user_id):
        return await self.bot.db.fetchrow("SELECT EXISTS(SELECT 1 FROM economy WHERE user_id=$1)", user_id)

    @commands.Cog.listener()
    async def on_message(self, message):
        author = message.author.id
        ctx = await self.bot.get_context(message)

        if message.author.bot or ctx.valid:
            return

        check = await self.user_check(author)

        new = self.gen_currency()

        if check[0]:
            result = await self.bot.db.fetchrow("SELECT amount, cd FROM economy WHERE user_id=$1", author)
            if time.time() - result["cd"] >= 120:
                await self.bot.db.execute("UPDATE economy SET amount=$1, cd=$2 WHERE user_id=$3",
                                          result["amount"] + new, time.time(), author)
        else:
            await self.bot.db.execute("INSERT INTO economy (user_id, amount, cd) VALUES ($1, $2, $3)",
                                      author, new, time.time())

    @commands.command()
    async def balance(self, ctx):
        check = await self.user_check(ctx.author.id)

        if check[0]:
            result = await self.bot.db.fetchrow("SELECT amount FROM economy WHERE user_id=$1", ctx.author.id)
            await ctx.send(f"💎 | You have **{result['amount']}** credits.")
        else:
            await ctx.send("You haven't earned any credits yet!")


def setup(bot):
    bot.add_cog(Economy(bot))
