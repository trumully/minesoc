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
            await self.bot.db.execute("UPDATE levels SET color = $1 WHERE user_id = $2 AND guild_id = $3",
                                      color.value, member, guild)
        embed = discord.Embed(color=color, title=f"Changed your color to `{color}`")
        await ctx.send(embed=embed)

    @profile.command(pass_context=True, name="background", aliases=["bg"])
    async def profile_background(self, ctx, image: str = None):
        """Changes the background image of your rank card. Change image to "default" to reset your background image."""
        available_bgs = [file.name[:-4] for file in (self.bot.path / "backgrounds").iterdir()]

        if image not in available_bgs and image != "default" or image is None:
            return await ctx.send(f"List of available backgrounds:\n```{', '.join(available_bgs)}```")

        member = ctx.author.id
        guild = ctx.guild.id

        await self.bot.db.execute("UPDATE levels SET bg = $1 WHERE user_id = $2 AND guild_id = $3",
                                  image, member, guild)

        embed = discord.Embed()
        embed.title = f"Changed your image to `{image}`" if image != "default" else "Reset your profile background."
        await ctx.send(embed=embed)

    @commands.command(pass_context=True, aliases=["lb", "ranks", "levels"])
    async def leaderboard(self, ctx):
        """Shows the top 10 users of your guild."""
        guild_check = ctx.guild is not None
        if guild_check:
            guild = ctx.guild.id

            users = await self.bot.db.fetch("SELECT * FROM levels WHERE guild_id = $1 ORDER BY xp DESC", guild)

            user_info = ""
            user_name = ""
            rankings = ""
            for index, value in zip(range(10), users):
                user = self.bot.get_user(value["user_id"])
                if user:
                    rank = index + 1
                    if rank <= 3:
                        if rank == 1:
                            top_user = f"Top Member: 🏆 **{str(user)}**"
                        rank = f"{self.leaderboard_emojis[rank]}\n"
                    else:
                        rank = f"#{rank}\n"
                    rankings += rank
                    xp_to_next = round((4 * (value["lvl"] ** 3) / 5))
                    user_info += f"Level {value['lvl']} ({value['xp']}/{xp_to_next})\n"
                    user_name += f"**{user.name}**\n"
            else:
                rankings += "...\n"
                user_info += "...\n"
                user_name += "...\n"

            embed = discord.Embed(color=ctx.me.colour, title=f"Top 10 in {ctx.guild.name}", description=top_user,
                                  timestamp=ctx.message.created_at)

            author = await self.bot.db.fetchrow("SELECT * FROM levels WHERE user_id = $1 AND guild_id = $2",
                                                ctx.author.id, guild)

            author_check = [i for i, j in enumerate(users) if j == author]

            if author_check:
                rankings += author_check[0]
                xp_to_next = round((4 * (author["lvl"] ** 3) / 5))
                user_info += f"Level {author['lvl']} ({author['xp']})/({xp_to_next})"
                user_name += ctx.author.name

            embed.add_field(name="Rank", value=rankings, inline=True)
            embed.add_field(name="Member", value=user_name, inline=True)
            embed.add_field(name="Level", value=user_info, inline=True)

            await ctx.send(embed=embed)

    @profile_color.error
    async def color_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send("That's not a valid color! Try a hex value (e.g #FF0000) or Discord color (e.g blurple).")


def setup(bot):
    bot.add_cog(Levels(bot))
