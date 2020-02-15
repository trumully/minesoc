import discord

from discord.ext import commands
from minesoc.utils import config


class Polls(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.polls = config.File("polls.json")

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
        options = {reactions[x]: option for x, option in enumerate(options)}

        embed = discord.Embed(color=discord.Color.blue())
        embed.title = name
        embed.description = "\n".join(f"{emoji} {option}" for emoji, option in options.items())

        message = await ctx.send(embed=embed)
        embed.set_footer(text=f"Poll ID: {message.id}")
        await message.edit(embed=embed)
        for emoji in options:
            await message.add_reaction(emoji)

        self.polls[ctx.guild.id] = {message.id: options}
        await ctx.send(self.polls)

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

        options = self.polls[ctx.guild.id][msg.id]
        await ctx.send(self.polls)

        tally = {x: 0 for x in options.keys()}
        for reaction in msg.reactions:
            if reaction.emoji in options.keys():
                tally[reaction.emoji] = reaction.count - 1 if reaction.count > 1 else 0

        poll_title = embed.title
        result = "\n".join(f"{self.polls[poll_id][key]} {tally[key]}" for key in tally.keys())
        await ctx.send(f"Result of poll for '{poll_title}':\n{result}")


def setup(bot):
    bot.add_cog(Polls(bot))
