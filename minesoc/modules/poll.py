import discord
import asyncpg

from discord.ext import commands


class Polls(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.bot.loop.create_task(self.create_table())

    async def create_table(self):
        await self.bot.wait_until_ready()

        query = "CREATE TABLE IF NOT EXISTS polls(id bigint NOT NULL UNIQUE, title text NOT NULL, options text ARRAY[" \
                "10]) "

        await self.bot.db.execute(query)

    @commands.group(name="poll")
    async def poll(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @poll.command(name="create")
    async def poll_create(self, ctx, name, *options):
        if len(options) <= 1:
            return await ctx.send("You need more than 1 option to make a poll.")
        if len(options) > 10:
            return await ctx.send("Your poll can't have more than 10 options.")

        reactions = ['1⃣', '2⃣', '3⃣', '4⃣', '5⃣', '6⃣', '7⃣', '8⃣', '9⃣', '🔟']
        options = [[reactions[x], option] for x, option in enumerate(options)]

        embed = discord.Embed(color=discord.Color.blue())
        embed.title = name
        embed.description = "\n".join(f"{emoji} {option}" for emoji, option in options)

        message = await ctx.send(embed=embed)

        embed.set_footer(text=f"Poll ID: {message.id}")
        await message.edit(embed=embed)

        for i in options:
            await message.add_reaction(i[0])

        await self.bot.db.execute("INSERT INTO polls(id, title, options) VALUES($1, $2, $3)", message.id, name, options)

    @poll.command(name="tally")
    async def poll_tally(self, ctx, poll_id):
        msg = await ctx.fetch_message(poll_id)
        if not msg.embeds:
            return
        embed = msg.embeds[0]
        if msg.author != ctx.guild.me:
            return
        if not embed.footer.text.startswith("Poll ID:"):
            return

        poll = await self.bot.db.fetchrow("SELECT * FROM polls WHERE id=$1", msg.id)

        options = {i: j for i, j in poll["options"]}

        tally = {x[0]: 0 for x in options.keys()}
        for reaction in msg.reactions:
            if reaction.emoji in options.keys():
                tally[reaction.emoji] = reaction.count - 1 if reaction.count > 1 else 0

        result = discord.Embed(color=discord.Color.blue())
        result.title = f"Results for '{embed.title}'"
        result.add_field(name="Option", value="\n".join(str(options[key]) for key in tally.keys()))
        result.add_field(name="Amount", value="\n".join(str(tally[key]) for key in tally.keys()))

        await ctx.send(embed=result)
        await self.bot.db.executemany("DELETE FROM polls WHERE id=$1", msg.id)


def setup(bot):
    bot.add_cog(Polls(bot))
