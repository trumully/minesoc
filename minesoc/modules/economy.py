# economy.py
# Money! Money! Money!

from discord.ext import commands


class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.bot.loop.create_task(self.economy_table())

    async def economy_table(self):
        await self.bot.wait_until_ready()
        await self.bot.db.execute("CREATE TABLE IF NOT EXISTS economy(user_id BIGINT, amount BIGINT)")

    async def user_check(self, user_id):
        return await self.bot.db.fetchrow("SELECT EXISTS(SELECT 1 FROM economy WHERE user_id=$1)", user_id)

    @commands.Cog.listener()
    async def on_message(self, message):
        author = message.author.id

        if self.user_check(author):
            await self.bot.db.execute("UPDATE economy SET amount=amount+5 WHERE user_id=$1", author)
        else:
            await self.bot.db.execute("INSERT INTO economy (user_id, amount) VALUES ($1, 5)", author)

    @commands.command()
    async def balance(self, ctx):
        if self.user_check(ctx.author.id):
            balance = await self.bot.db.fetchrow("SELECT amount FROM economy WHERE user_id=$1", ctx.author.id)
            await ctx.send(f"💎 | You have **{balance}** credits.")
        else:
            await ctx.send("You haven't earned any credits yet!")


def setup(bot):
    bot.add_cog(Economy(bot))
