import asyncio
import string
import time
import discord

from random import choice, choices, randint
from discord.ext import commands

_8ball = ["It is certain.", "It is decidedly so.", "Without a doubt.", "Yes - definitely.", "You may rely on it.",
          "As I see it, yes.", "Most likely.", "Outlook good.", "Yes.", "Signs point to yes", "Reply hazy, try again.",
          "Ask again later.", "Better not tell you now.", "Cannot predict now.", "Concentrate and ask again",
          "Don't count on it.", "My reply is no.", "My sources say no.", "Outlook not so good.", "Very doubtful"]


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def robohash(self, query, set_num, author):
        query = "".join(choices(string.ascii_uppercase + string.digits, k=3)) if query is None else query
        embed = discord.Embed(color=self.bot.colors.neutral)
        embed.set_image(url=f"https://robohash.org/{query}.png?set=set{set_num}")
        embed.set_footer(text=f"Requested by {author.name} | Provided by robohash.org", icon_url=author.avatar_url)

        return embed

    async def user_check(self, user_id):
        return await self.bot.db.fetchrow("SELECT EXISTS(SELECT 1 FROM economy WHERE user_id=$1)", user_id)

    @commands.command()
    async def cat(self, ctx):
        """Returns a random image of a cat."""
        async with ctx.typing():
            await ctx.send(embed=(await self.bot.api.animal.fetch_cat()).embed)

    @commands.command()
    async def dog(self, ctx, breed: str = None, sub_breed: str = None):
        """Returns a random image of a dog."""
        async with ctx.typing():
            await ctx.send(embed=(await self.bot.api.animal.fetch_dog(breed, sub_breed)).embed)

    @commands.group(aliases=["robo", "rh"])
    async def robohash(self, ctx):
        """Get randomly generated images from robohash.org"""
        if ctx.invoked_subcommand is None:
            await ctx.send(embed=self.robohash(None, randint(1, 5), ctx.author))

    @robohash.command()
    async def robot(self, ctx, *, query: str = None):
        """Get a randomly generated robot from robohash.org"""
        await ctx.send(embed=self.robohash(query, 1, ctx.author))

    @robohash.command()
    async def monster(self, ctx, *, query: str = None):
        """Get a randomly generated monster from robohash.org"""
        await ctx.send(embed=self.robohash(query, 2, ctx.author))

    @robohash.command()
    async def robohead(self, ctx, *, query: str = None):
        """Get a randomly generated robohead from robohash.org"""
        await ctx.send(embed=self.robohash(query, 3, ctx.author))

    @robohash.command()
    async def kitten(self, ctx, *, query: str = None):
        """Get a randomly generated kitten from robohash.org"""
        await ctx.send(embed=self.robohash(query, 4, ctx.author))

    @robohash.command()
    async def human(self, ctx, *, query: str = None):
        """Get a randomly generated human from robohash.org"""
        await ctx.send(embed=self.robohash(query, 5, ctx.author))

    @commands.command(aliases=["choice"])
    async def choose(self, ctx, *options):
        """Having trouble making a decision? I'll make it for you!"""
        await ctx.send(f"I choose: {choice(options)}")

    @commands.command(name="8ball")
    async def _8ball(self, ctx, *, query):
        """Let the Magic 8 Ball decide your fate."""
        await ctx.send(f"> {query}\n🎱 {choice(_8ball)}")

    @commands.command()
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def trivia(self, ctx):
        """Do some trivia."""
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
                        result = await self.bot.db.fetchrow("SELECT * FROM economy WHERE user_id=$1", ctx.author.id)
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

    @commands.command()
    async def ship(self, ctx, thing_1, thing_2):
        match = randint(1, 100)
        thing_1 = thing_1.display_name if isinstance(thing_1, discord.Member) else thing_1
        thing_2 = thing_2.display_name if isinstance(thing_2, discord.Member) else thing_2

        responses = ["Bad 😢", "Meh 😐", "Good 🙂", "Pretty Good 😃", "Wow 😍", "PERFECT ❣️"]
        message = f"💗**MATCHMAKING**💗\n🔻 `{thing_1}`\n🔺 `{thing_2}`"
        embed = discord.Embed(color=discord.Color(0xFF1493))

        progress = ["█" for _ in range(round(match, -1) // 10)]
        if len(progress) < 10:
            for i in range(10 - len(progress)):
                progress.append(" ​")
        response = f"**{match}%** `{progress}` "
        if match < 20:
            response += responses[0]
        elif 40 > match >= 20:
            response += responses[1]
        elif 60 > match >= 40:
            response += responses[2]
        elif 80 > match >= 60:
            response += responses[3]
        elif 99 > match >= 80:
            response += responses[4]
        else:
            response += responses[5]

        embed.description = response

        await ctx.send(message, embed=embed)


def setup(bot):
    bot.add_cog(Fun(bot))
