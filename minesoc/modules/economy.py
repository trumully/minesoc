# economy.py
# Money! Money! Money!
import time
import random
import discord

from discord.ext import commands
from libneko.aggregates import Proxy

COOLDOWN = 120  # 2 minutes
STREAK_TIMER = 3600 * 44  # 44 hours
STREAK_CD = 3600 * 24  # 24 hours


def seconds_to_hms(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    if hour == 0:
        return "%02d minutes, %02d seconds" % (minutes, seconds)
    return "%d hours, %02d minutes, %02d seconds" % (hour, minutes, seconds)


class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.credit_gain = Proxy(min=10, max=50)
        self.daily_gain = 200

    def gen_currency(self):
        return random.randint(self.credit_gain.min, self.credit_gain.max)

    async def get_items(self):
        return await self.bot.db.fetch("SELECT * FROM items")

    async def user_check(self, user_id):
        return await self.bot.db.fetchrow("SELECT EXISTS(SELECT 1 FROM economy WHERE user_id=$1)", user_id)

    @commands.Cog.listener()
    async def on_message(self, message):
        author = message.author.id
        ctx = await self.bot.get_context(message)

        if message.author.bot or ctx.valid:
            return

        check = await self.user_check(author)

        gain = self.gen_currency()

        if check[0]:
            result = await self.bot.db.fetchrow("SELECT * FROM economy WHERE user_id=$1", author)
            if time.time() - result["cd"] >= COOLDOWN:
                await self.bot.db.execute("UPDATE economy SET amount=$1, cd=$2 WHERE user_id=$3",
                                          result["amount"] + gain, time.time(), author)
        else:
            await self.bot.db.execute("INSERT INTO economy (user_id, amount, cd, streak, streak_time, streak_cd) "
                                      "VALUES ($1, $2, $3, 0, 0, 0)", author, gain, time.time())

    @commands.command()
    async def balance(self, ctx):
        check = await self.user_check(ctx.author.id)

        if check[0]:
            result = await self.bot.db.fetchrow("SELECT amount FROM economy WHERE user_id=$1", ctx.author.id)
            await ctx.send(f"💎 | **{ctx.author.name}**, you have **${result['amount']}** credits.")
        else:
            await ctx.send(f"❗ | **{ctx.author.name}** You haven't earned any credits yet!")

    @commands.command()
    async def daily(self, ctx):
        author = ctx.author.id

        check = await self.user_check(author)

        if check[0]:
            result = await self.bot.db.fetchrow("SELECT * FROM economy WHERE user_id=$1", author)
            if (time_diff := time.time() - result["streak_cd"]) >= STREAK_CD:

                if time.time() - result["streak_time"] >= STREAK_TIMER and result["streak_time"] > 0:
                    streak = 1
                else:
                    streak = result["streak"] + 1

                msg = f"💸 | **{ctx.author.name}**, you got ${self.daily_gain} credits!\n\n**Streak: {streak}**"

                if streak % 5 == 0 and streak > 0:
                    streak_bonus = self.gen_currency() * 2
                    net_gain = self.daily_gain + streak_bonus
                    msg += f"\n\n**You completed a streak and earned an extra ${streak_bonus} credits " \
                           f"({net_gain} total)!**"
                else:
                    net_gain = self.daily_gain

                await self.bot.db.execute("UPDATE economy SET amount=$1, streak=$2, streak_time=$3 WHERE user_id=$4",
                                          result["amount"] + net_gain, streak, time.time(), author)
            else:
                msg = f"❗ | **{ctx.author.name}**, you're on cooldown! Try again in {seconds_to_hms(time_diff)}"

        else:
            await self.bot.db.execute("INSERT INTO economy (user_id, amount, cd, streak, streak_time) "
                                      "VALUES ($1, $2, $3, 1, $4)", author, self.daily_gain, time.time(), time.time())

            msg = f"💸 | **{ctx.author.name}**, you got ${self.daily_gain} credits!\n\n**Streak: 1**"

        await ctx.send(msg)

    @commands.group(name="shop")
    async def shop(self, ctx):
        if ctx.invoked_subcommand is None:
            items = [f"[+] {item['name']} - {item['price']}" for item in await self.get_items()]
            if not items:
                return await ctx.send("Shop is empty. Check back later!")
            items_string = "\n".join(items)
            shop = discord.Embed(title="Shop", description=f"```py\n{items_string}```")
            await ctx.send(embed=shop)

    @shop.command(name="buy", aliaes=["purchase"])
    async def shop_buy(self, ctx, *, item: str):
        item_to_buy = None
        for i in await self.get_items():
            if item.lower() == i["name"]:
                item_to_buy = i

        author = ctx.author
        if item_to_buy:
            user = await self.bot.db.fetchrow("SELECT amount FROM economy WHERE user_id=$1", author.id)
            if (amount := user["amount"] - item_to_buy["price"]) >= 0:
                await self.bot.db.execute("UPDATE economy SET amount=$1 WHERE user_id=$2", amount, author.id)
                await self.bot.db.execute("UPDATE inventory SET inventory::int[] = inventory || $1 WHERE "
                                          "user_id = $2 AND ($1 == ANY(inventory) IS NOT TRUE)", int(item_to_buy["id"]),
                                          author.id)
                await ctx.success(f"{author.name}, you purchased {item_to_buy['name']} for {item_to_buy['price']} "
                                  f"credits!")
        else:
            await ctx.send(f"**{author.name}** that item does not exist! Make sure you typed the item name correctly.")


def setup(bot):
    bot.add_cog(Economy(bot))
