# levels.py
# This extension handles level ups

from io import BytesIO
from itertools import count

import aiohttp.client
import discord
import asyncpg

from discord.ext import commands
from minesoc.utils import images
from pathlib import Path


class Levels(commands.Cog):
    """Commands relating to the leveling system."""

    def __init__(self, bot):
        self.bot = bot
        self.leaderboard_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}

        self.bot.loop.create_task(self.create_table())

    async def create_table(self):
        await self.bot.wait_until_ready()

        query = "CREATE TABLE IF NOT EXISTS levels(user_id BIGINT, guild_id BIGINT, xp BIGINT, lvl INT, cd REAL, " \
                "color INT, bg TEXT)"

        await self.bot.db.execute(query)

    async def cog_before_invoke(self, ctx):
        persistence = await self.bot.db.fetchrow("SELECT lvls FROM persistence WHERE guild=$1", ctx.guild.id)
        if not persistence["lvls"]:
            raise commands.DisabledCommand

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.DisabledCommand):
            await ctx.error(description="The level system has been disabled for this guild.")

    @commands.group(invoke_without_command=True)
    @commands.bot_has_permissions(attach_files=True)
    async def profile(self, ctx, member: discord.Member = None):
        """Change the appearance of your rank card."""
        if ctx.invoked_subcommand is None:
            member = member or ctx.author

            if member.bot:
                return

            profile = images.Profile()

            member_id = member.id
            guild_id = ctx.guild.id

            user = await self.bot.db.fetchrow("SELECT * FROM levels WHERE user_id = $1 AND guild_id = $2",
                                              member_id, guild_id)
            if user:
                async with ctx.typing(), aiohttp.ClientSession() as session:
                    async with session.get(f"{member.avatar_url}") as r:
                        profile_bytes = await r.read()

                buffer = profile.draw(str(member.display_name), user["lvl"], user["xp"], BytesIO(profile_bytes),
                                      discord.Color(user["color"]).to_rgb(), user["bg"])

                await ctx.send(file=discord.File(fp=buffer, filename="rank_card.png"))
            else:
                await ctx.send(f"**{ctx.author.name}**, "
                               f"{'this member has not' if member != ctx.author else 'you have not'} received XP yet.")

    @profile.command(pass_context=True, name="color", aliases=["colour"])
    async def profile_color(self, ctx, *, color: discord.Color):
        """Change the accent color used of your rank card."""
        member = ctx.author.id
        guild = ctx.guild.id
        async with ctx.typing():
            await self.bot.db.execute("UPDATE levels SET color=$1 WHERE user_id=$2 AND guild_id=$3", color.value,
                                      member, guild)
        embed = discord.Embed(color=color, title=f"Changed your color to `{color}`")
        await ctx.send(embed=embed)

    @profile.command(pass_context=True, name="background", aliases=["bg"])
    async def profile_background(self, ctx, bg: str = None):
        """Changes the background image of your rank card. Change image to "default" to reset your background image."""
        bg = bg.lower() if bg is not None else bg

        user = await self.bot.db.fetchrow("SELECT * FROM inventory WHERE user_id=$1", ctx.author.id)
        bgs = await self.bot.db.fetch("SELECT * FROM items WHERE type=0")

        inventory = user["items"]
        owned_bgs = [j["name"] for i in inventory for j in bgs if i == j["id"]]
        available_bgs = [file.name[:-4] for file in (self.bot.path / "backgrounds").iterdir() if file.name[:-4]]

        if bg is None or bg not in available_bgs and bg not in owned_bgs and bg != "default":
            owned_bgs = "\n".join(f"[+] {i.title()}" for i in owned_bgs)
            if not owned_bgs:
                return await ctx.send(f"**{ctx.author.name}**, you don't own any backgrounds!")
            embed = discord.Embed(title="Available Backgrounds", description=f"```\n{owned_bgs}```")
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
            return await ctx.send(embed=embed)

        member = ctx.author.id
        guild = ctx.guild.id

        if bg in owned_bgs:
            await self.bot.db.execute("UPDATE levels SET bg = $1 WHERE user_id = $2 AND guild_id = $3",
                                      bg, member, guild)
            embed = discord.Embed()
            embed.title = f"Changed your image to `{bg}`" if bg != "default" else "Reset your profile background."
            await ctx.send(embed=embed)
        else:
            await ctx.send("You do not own that background!")

    @commands.command(pass_context=True, aliases=["lb", "ranks", "levels"])
    async def leaderboard(self, ctx):
        """Shows the top 10 users of your guild."""
        guild_check = ctx.guild is not None

        if guild_check:
            guild = ctx.guild.id

            users = await self.bot.db.fetch("SELECT * FROM levels WHERE guild_id=$1 ORDER BY xp DESC LIMIT 10", guild)

            ranks = {(y := x + 1): f"#{y}" if y > 3 else f"{self.leaderboard_emojis[y]}" for x in range(10)}

            fields = {"member": [], "level": [], "rank": []}
            for index, value in zip(range(10), users):
                user = self.bot.get_user(value["user_id"])

                if (rank := index + 1) == 1:
                    top_user = f"Top Member: 🏆 **{str(user)}**"

                if user:
                    fields["rank"].append(ranks[rank])
                    fields["member"].append(f"**{user.name}**")
                    fields["level"].append(f"Level {value['lvl']} ({value['xp']}/{round((4 * (value['lvl'] ** 3) / 5))})")
            else:
                for value in fields.values():
                    value.append("...")

            embed = discord.Embed(color=ctx.me.colour, title=f"Top 10 in {ctx.guild.name}", description=top_user,
                                  timestamp=ctx.message.created_at)

            author = await self.bot.db.fetchrow("SELECT * FROM levels WHERE user_id=$1 AND guild_id=$2",
                                                ctx.author.id, guild)

            if author in users:
                fields["rank"].append(ranks[users.index(author) + 1])
                fields["member"].append(f"**{ctx.author.name}**")
                xp = round((4 * (author['lvl'] ** 3) / 5))
                fields["level"].append(f"Level {author['lvl']} ({author['xp']}/{xp})")

            embed.add_field(name="Rank", value="\n".join(fields["rank"]), inline=True)
            embed.add_field(name="Member", value="\n".join(fields["member"]), inline=True)
            embed.add_field(name="Level", value="\n".join(fields["level"]), inline=True)

            await ctx.send(embed=embed)

    @profile_color.error
    async def color_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send("That's not a valid color! Try a hex value (e.g #FF0000) or Discord color (e.g blurple).")


def setup(bot):
    bot.add_cog(Levels(bot))
