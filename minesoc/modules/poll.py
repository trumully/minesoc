import discord

from discord.ext import commands


class Polls(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.polls = {}

    async def __generate_poll(self, name, options: dict, channel):
        self.name = name
        self.options = options

        embed = discord.Embed(color=discord.Color.blue())
        embed.title = name
        embed.description = "\n".join(f"{emoji} {option}" for emoji, option in options.items())

        message = await channel.send(embed=embed)
        embed.set_footer(text=f"Poll ID: {message.id}")
        await message.edit(message, embed=embed)
        for emoji in options:
            await message.add_reaction(emoji)

        self.polls[message.id] = options

    async def __get_result(self, message):
        tally = {x: 0 for x in self.options.keys()}
        for reaction in message.reactions:
            if reaction.emoji in self.options.keys():
                tally[reaction.emoji] = reaction.count - 1 if reaction.count > 1 else 0  # omits the bot's vote.

        return tally

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

        await self.__generate_poll(name, options, ctx.channel)

    @poll.command(name="tally")
    async def poll_tally(self, ctx, poll_id):
        msg = await ctx.fetch_message(poll_id)
        embed = msg.embeds[0]
        if not msg or msg.author != ctx.author or embed["footer"]["text"].startswith("Poll ID:"):
            return

        tally = await self.__get_result(poll_id)

        poll_title = embed["title"]
        result = "\n".join(f"{self.polls[poll_id][key]} {tally[key]}" for key in tally.keys())
        await ctx.send(f"Result of poll for '{poll_title}':\n{result}")


def setup(bot):
    bot.add_cog(Polls(bot))
