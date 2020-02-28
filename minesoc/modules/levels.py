# levels.py
# This extension handles level ups

import discord
import aiohttp.client

from discord.ext import commands
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps
from os import listdir
from math import log, floor

# leveling system
# 1. create table if it doesn't exist
# 2. assign each user xp, lvl, cd if they don't have it already
# 3. fetch all users from server
# 4. if a user's message count has increased and their cd time has elapsed, give them xp
# 5. if this amount of xp results in a level up, send a level up message in channel of original message
# 6. reset user's cd time


class Rank:
    def __init__(self):
        self.font = ImageFont.truetype("arialbd.ttf", 28*2)
        self.medium_font = ImageFont.truetype("arialbd.ttf", 22*2)
        self.small_font = ImageFont.truetype("arialbd.ttf", 16*2)

    def human_format(self, number):
        units = ['', 'K', 'M', 'G', 'T', 'P']
        k = 1000.0
        magnitude = int(floor(log(number, k)))
        return '%.2f%s' % (number / k ** magnitude, units[magnitude])

    def draw(self, user, lvl, xp, profile_bytes: BytesIO, color, bg):
        profile_bytes = Image.open(profile_bytes)
        size = (240, 240)
        profile_bytes = profile_bytes.resize(size)
        if bg is not None and bg != "default":
            bg_img = Image.open(f"backgrounds/{bg}.jpg")
            im = ImageOps.fit(bg_img, (800, 296), centering=(0.0, 0.0))
        else:
            im = Image.new("RGBA", (800, 296), (44, 44, 44, 255))

        im_draw = ImageDraw.Draw(im)

        # User name
        name = user.name
        im_draw.text((350, 10), name, font=self.font, fill=color)

        # Level
        lvl_text = f"LEVEL {lvl}"
        im_draw.text((350, 74), lvl_text, font=self.medium_font, fill=(255, 255, 255, 255))

        xp_to_next = round((4 * (lvl ** 3) / 5))
        progress = xp / xp_to_next

        # XP progress
        xp_text = f"{xp if xp < 1000 else self.human_format(xp)} / {xp_to_next if xp_to_next < 1000 else self.human_format(xp_to_next)}"
        im_draw.text((350, 124), xp_text, font=self.small_font, fill=(255, 255, 255, 255))

        # XP progress bar
        im_draw.rectangle((350, 190, 750, 250), fill=(64, 64, 64, 255))
        im_draw.rectangle((350, 190, 350 + int(400 * progress), 125*2), fill=color)

        # Avatar border
        im_draw.ellipse((0, 0, 280, 280), fill=color)

        # Avatar
        circle = Image.open("images/circle.png")
        im.paste(profile_bytes, (20, 20), circle)

        buffer = BytesIO()
        im.save(buffer, "png")
        buffer.seek(0)

        return buffer


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

            rankcard = Rank()

            member_id = member.id
            guild_id = ctx.guild.id

            user = await self.bot.db.fetchrow("SELECT * FROM levels WHERE user_id = $1 AND guild_id = $2",
                                              member_id, guild_id)

            if user:
                async with ctx.typing(), aiohttp.ClientSession() as session:
                    async with session.get(f"{member.avatar_url}") as r:
                        profile_bytes = await r.read()

                buffer = rankcard.draw(member, user["lvl"], user["xp"], BytesIO(profile_bytes),
                                       discord.Color(user["color"]).to_rgb(), user["bg"])

                await ctx.send(file=discord.File(fp=buffer, filename="rank_card.png"))
            else:
                await ctx.send("Member hasn't received xp yet.")

    @profile.command(pass_context=True, name="color", aliases=["colour"])
    async def profile_color(self, ctx, *, color: discord.Color):
        """Change the highlight color used of your rank card."""
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
        available_bgs = []

        for file in listdir("backgrounds/"):
            available_bgs.append(str(file[:-4]))

        if image not in available_bgs and image != "default" or image is None:
            return await ctx.send(f"List of available backgrounds:\n```{', '.join(available_bgs)}```")

        member = ctx.author.id
        guild = ctx.guild.id

        await self.bot.db.execute("UPDATE levels SET bg = $1 WHERE user_id = $2 AND guild_id = $3",
                                  image, member, guild)

        await ctx.send(embed=discord.Embed(title=f"Changed your image to `{image}`" if image != "default" else
                       "Reset your profile background."))

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
            for idx, val in zip(range(10), users):
                user = self.bot.get_user(val["user_id"])
                if user:
                    rank = idx + 1
                    if rank <= 3:
                        if rank == 1:
                            top_user = f"Top Member: 🏆 **{str(user)}**"
                        rank = f"{self.leaderboard_emojis[rank]}\n"
                    else:
                        rank = f"#{rank}\n"
                    rankings += rank
                    user_name += f"**{user.name}**\n"
                    xp_to_next = round((4 * (val["lvl"] ** 3) / 5))
                    user_info += f"Level {val['lvl']} ({val['xp']}/{xp_to_next})\n"

            embed = discord.Embed(color=ctx.me.colour,
                                  title=f"Top 10 in {ctx.guild.name}",
                                  description=top_user,
                                  timestamp=ctx.message.created_at)
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
