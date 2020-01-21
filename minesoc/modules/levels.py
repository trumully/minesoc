# levels.py
# This extension handles level ups

import discord
import aiosqlite
import time
import aiohttp.client

from random import randint
from discord.ext import commands
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# leveling system
# 1. create table if it doesn't exist
# 2. assign each user xp, lvl, cd if they don't have it already
# 3. fetch all users from server
# 4. if a user's message count has increased and their cd time has elapsed, give them xp
# 5. if this amount of xp results in a level up, send a level up message in channel of original message
# 6. reset user's cd time


class Rank:
    def __init__(self):
        self.font = ImageFont.truetype("arialbd.ttf", 28)
        self.medium_font = ImageFont.truetype("arialbd.ttf", 22)
        self.small_font = ImageFont.truetype("arialbd.ttf", 16)

    def draw(self, user, lvl, xp, profile_bytes: BytesIO, color):
        RGB = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        profile_bytes = Image.open(profile_bytes)
        im = Image.new("RGBA", (400, 148), (44, 44, 44, 255))

        im_draw = ImageDraw.Draw(im)
        im_draw.text((154, 5), user, font=self.font, fill=(RGB[0], RGB[1], RGB[2], 255))

        lvl_text = f"LEVEL {lvl}"
        im_draw.text((154, 37), lvl_text, font=self.medium_font, fill=(255, 255, 255, 255))

        xp_text = f"{xp}/{round((4 * (lvl ** 3) / 5))}"
        im_draw.text((154, 62), xp_text, font=self.small_font, fill=(255, 255, 255, 255))

        im_draw.rectangle((174, 95, 374, 125), fill=(64, 64, 64, 255))
        im_draw.rectangle((174, 95, 174 + (int(xp / round((4 * (lvl ** 3) / 5)) * 100)) * 2, 125),
                          fill=(221, 221, 221, 255))

        im_draw.rectangle((0, 0, 148, 148), fill=(RGB[0], RGB[1], RGB[2], 255))
        im.paste(profile_bytes, (10, 10))

        buffer = BytesIO()
        im.save(buffer, "png")
        buffer.seek(0)

        return buffer


class Levels(commands.Cog):
    """Commands relating to the leveling system."""

    def __init__(self, bot):
        self.bot = bot

        self.bot.loop.create_task(self.create_table())

    async def lvl_up(self, user, ctx):
        cur_xp = user['xp']
        cur_lvl = user['lvl']

        if cur_xp >= round((4 * (cur_lvl ** 3) / 5)):  # lvl 1: 1 xp, lvl 2: 2 xp, lvl 3: 26xp
            await ctx.send(
                f"🆙 | **{self.bot.get_user(user['user_id']).name}** leveled up to **Level {user['lvl'] + 1}**!")
            return True
        else:
            return False

    async def create_table(self):
        await self.bot.wait_until_ready()

        async with aiosqlite.connect('level_system.db') as db:
            await db.execute('''CREATE TABLE IF NOT EXISTS users(
                                user_id integer,
                                guild_id integer,
                                xp integer,
                                lvl integer,
                                cd real
                                )''')
            await db.commit()

    @commands.Cog.listener()
    async def on_message(self, message):
        ctx = await self.bot.get_context(message)

        if message.author.bot or ctx.valid:
            return

        else:
            author_id = str(message.author.id)
            guild_id = str(message.guild.id)

            db = await aiosqlite.connect("level_system.db")
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT user_id, guild_id, xp, lvl, cd FROM users "
                                      "WHERE user_id=:u_id AND guild_id=:g_id", {"u_id": author_id, "g_id": guild_id})
            user = await cursor.fetchone()

            if not user:
                db.row_factory = aiosqlite.Row
                await db.execute("INSERT INTO users VALUES (:u_id, :g_id, :xp, :lvl, :cd)",
                                 {"u_id": author_id, "g_id": guild_id, "xp": 0, "lvl": 1, "cd": time.time()})
                await db.commit()
                user = await cursor.fetchone()

            xp_gain = randint(1, 7)
            new_xp = user["xp"] + xp_gain

            time_diff = time.time() - user["cd"]
            if time_diff >= 120:
                await cursor.execute("UPDATE users SET xp=:xp, cd=:cd WHERE user_id=:u_id AND guild_id=:g_id",
                                     {"xp": new_xp, "u_id": author_id, "g_id": guild_id, "cd": time.time()})
                await db.commit()

            if await self.lvl_up(user, ctx):
                await cursor.execute("UPDATE users SET lvl=:lvl WHERE user_id=:u_id AND guild_id=:g_id",
                                     {"lvl": user["lvl"] + 1, "u_id": author_id, "g_id": guild_id})
                await db.commit()

    # Commands
    @commands.command(pass_context=True, aliases=["lvl", "lev"])
    async def level(self, ctx, member: discord.Member = None):
        """
        Get the level of yourself or another member.
        """
        rankcard = Rank()
        member = ctx.author if not member else member

        member_id = str(member.id)
        guild_id = str(ctx.guild.id)

        async with aiosqlite.connect("level_system.db") as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT user_id, guild_id, xp, lvl, cd "
                                  "FROM users WHERE user_id=:u_id AND guild_id=:g_id",
                                  {"u_id": member_id, "g_id": guild_id}) as cursor:
                user = await cursor.fetchone()

        async with ctx.typing():
            if user:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{member.avatar_url}?size=128") as r:
                        profile_bytes = await r.read()

                buffer = rankcard.draw(str(member.display_name), user["lvl"], user["xp"], BytesIO(profile_bytes),
                                       str(member.color).lstrip("#"))

                await ctx.send(file=discord.File(fp=buffer, filename="rank_card.png"))
            else:
                await ctx.send("Member hasn't received xp yet.")

    @commands.command(pass_context=True, aliases=["lb"])
    async def leaderboard(self, ctx):
        """
        Shows the top 10 users on the server.
        """
        guild_id = str(ctx.guild.id)

        async with aiosqlite.connect("level_system.db") as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT user_id, guild_id, xp, lvl "
                                  "FROM users WHERE guild_id=:g_id ORDER BY lvl DESC",
                                  {"g_id": guild_id}) as cursor:
                users = await cursor.fetchall()

        users_list = [dict(row) for row in users if not None]

        user_info = ""
        user_name = ""
        rankings = ""
        for idx, val in zip(range(10), users_list):
            user = self.bot.get_user(val["user_id"])
            if user:
                print(user)
                rankings += f"#{idx + 1}\n"
                user_name += f"**{user.name}**\n"
                xp_to_next = round((4 * (val["lvl"] ** 3) / 5))
                user_info += f"Level {val['lvl']} ({val['xp']}/{xp_to_next})\n"

        embed = discord.Embed(color=ctx.guild.get_member(self.bot.user.id).colour, title=f"Top 10 in {ctx.guild.name}",
                              timestamp=ctx.message.created_at)
        embed.add_field(name="Rank", value=rankings, inline=True)
        embed.add_field(name="User", value=user_name, inline=True)
        embed.add_field(name="Level", value=user_info, inline=True)

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Levels(bot))
