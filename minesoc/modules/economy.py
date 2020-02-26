# economy.py
# Money stuff

import discord
import random
from discord.ext import commands


class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.economy = "credits"

        self.bot.loop.create_task(self.create_economy_table())

    async def create_economy_table(self):
        await self.bot.wait_until_ready()

        q = "CREATE TABLE IF NOT EXISTS economy(user BIGINT, balance BIGINT)"

        await self.bot.db.execute(q)

    async def fetch_user(self, user_id):
        result = await self.bot.db.execute("SELECT * FROM economy WHERE user=$1", user_id)

        if not result:
            await self.bot.db.execute("INSERT INTO economy(user, balance) VALUES($1, 0)", user_id)
            result = await self.bot.db.execute("SELECT * FROM economy WHERE user=$1", user_id)

        return result

    @commands.command(aliases=["amount"])
    async def balance(self, ctx):
        user = await self.fetch_user(ctx.author.id)
        await ctx.send(f"🏦 You have **{user['balance']}** {self.economy}")

    @commands.command()
    async def get_money(self, ctx):
        moola = random.uniform(1, 200)
        await self.bot.db.execute("UPDATE economy SET balance=$1 WHERE user=$2", moola, ctx.author.id)

        user = await self.fetch_user(ctx.author.id)

        await ctx.send(f"YOU GOT {moola}!! proof: {user['balance']}")


def setup(bot):
    bot.add_cog(Economy(bot))
