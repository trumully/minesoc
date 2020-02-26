# economy.py
# Capitalism!

import discord

from discord.ext import commands
from datetime import datetime


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.economy_name = "credits"
        self.base_daily = 150
        self.streak_bonus = 20

        self.bot.loop.create_task(self.create_table())

    async def create_table(self):
        await self.bot.wait_until_ready()

        query = "CREATE TABLE IF NOT EXISTS economy(user BIGINT, amount BIGINT, last_daily TIMESTAMP, streaks INT)"

        await self.bot.db.execute(query)

    @commands.command()
    @commands.cooldown(1, 3600*24, commands.BucketType.user)
    async def daily(self, ctx):
        now = datetime.now()

        user = await self.bot.db.fetchrow("SELECT * FROM economy WHERE user=$1", ctx.author.id)

        if not user:
            await self.bot.db.execute("INSERT INTO economy(user, amount, last_daily, streaks) VALUES($1, $2, now, 0)",
                                      ctx.author.id, self.base_daily)
            await ctx.send(
                f"{self.bot.custom_emojis.green_tick} You got **${self.base_daily}** daily {self.economy_name}!"
            )

        else:
            difference = now - user["last_daily"]
            if difference.days < 2:
                if user["streaks"] + 1 % 5 == 0:
                    amount = self.base_daily + ((user["streaks"] + 1) * self.streak_bonus) + self.streak_bonus * 5
                else:
                    amount = self.base_daily + ((user["streaks"] + 1) * self.streak_bonus)

                await self.bot.db.execute("UPDATE economy SET amount=$1, streaks=$2, last_daily=now WHERE user=$3",
                                          amount, ctx.author.id, user["streaks"] + 1)

                await ctx.send(
                    f"{self.bot.custom_emojis.green_tick} You got **${amount}** daily {self.economy_name}!\n\n"
                    f"🔥 Current Streak: `{user['streaks'] + 1}"
                )

    @commands.command(aliases=["amount", "bank"])
    async def balance(self, ctx):
        user = await self.bot.db.fetchrow("SELECT * FROM economy WHERE user=$1", ctx.author.id)

        if user:
            await ctx.send(f"💎 You have **${user['amount']}** {self.economy_name}")
        else:
            await ctx.send(f"You haven't earned any {self.economy_name} yet.")


def setup(bot):
    bot.add_cog(Economy(bot))
