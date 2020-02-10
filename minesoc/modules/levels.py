# levels.py
# This extension handles level ups

import json
import discord
import aiosqlite
import aiohttp.client
import asyncio

from discord.ext import commands
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps
from os import listdir

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

    def draw(self, user, lvl, xp, profile_bytes: BytesIO, color, bg):
        if color == 0:
            RGB = (0, 0, 0)
        else:
            color = str(color)
            RGB = tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))

        profile_bytes = Image.open(profile_bytes)
        size = (256, 256)
        profile_bytes = profile_bytes.resize(size)
        if bg is not None and bg != "default":
            bg_img = Image.open(f"/opt/discord-v2/github/minesoc/backgrounds/{bg}.jpg")
            im = ImageOps.fit(bg_img, (800, 296), centering=(0.0, 0.0))
        else:
            im = Image.new("RGBA", (800, 296), (44, 44, 44, 255))

        im_draw = ImageDraw.Draw(im)
        im_draw.text((154*2, 5*2), user, font=self.font, fill=(RGB[0], RGB[1], RGB[2], 255))

        lvl_text = f"LEVEL {lvl}"
        im_draw.text((154*2, 37*2), lvl_text, font=self.medium_font, fill=(255, 255, 255, 255))

        xp_text = f"{xp}/{round((4 * (lvl ** 3) / 5))}"
        im_draw.text((154*2, 62*2), xp_text, font=self.small_font, fill=(255, 255, 255, 255))

        im_draw.rectangle((175*2, 95*2, 750, 125*2), fill=(64, 64, 64, 255))
        progress = xp / round((4 * (lvl ** 3) / 5))
        im_draw.rectangle((175*2, 95*2, 350 + int(400 * progress), 125*2), fill=(RGB[0], RGB[1], RGB[2], 255))

        im_draw.rectangle((0, 0, 148*2, 148*2), fill=(RGB[0], RGB[1], RGB[2], 255))

        # Rounded square mask.
        # rounded_square = Image.open("/opt/discord-v2/github/minesoc/square-rounded-256.png")
        # im.paste(profile_bytes, (10*2, 10*2), rounded_square)

        im.paste(profile_bytes, (10 * 2, 10 * 2))

        buffer = BytesIO()
        im.save(buffer, "png")
        buffer.seek(0)

        return buffer


class Levels(commands.Cog):
    """Commands relating to the leveling system."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.loop.create_task(self.create_table())

    async def create_table(self):
        await self.bot.wait_until_ready()

        query = "CREATE TABLE IF NOT EXISTS users(user_id INTEGER, guild_id INTEGER, xp INTEGER, " \
                "lvl INTEGER, cd REAL, color INTEGER, bg TEXT)"

        await self.bot.db.execute(query)

    @commands.group(invoke_without_command=True)
    async def profile(self, ctx, member: discord.Member = None):
        """Change the appearance of your rank card."""
        member = member or ctx.author

        if member.bot:
            return

        rankcard = Rank()

        member_id = str(member.id)
        guild_id = str(ctx.guild.id)

        self.bot.db.row_factory = aiosqlite.Row
        async with self.bot.db.execute("SELECT user_id, guild_id, xp, lvl, cd, color, bg "
                                       "FROM users WHERE user_id=:u_id AND guild_id=:g_id",
                                       {"u_id": member_id, "g_id": guild_id}) as cursor:
            user = await cursor.fetchone()

        if user:
            async with ctx.typing(), aiohttp.ClientSession() as session:
                async with session.get(f"{member.avatar_url}") as r:
                    profile_bytes = await r.read()

            buffer = rankcard.draw(str(member.display_name), user["lvl"], user["xp"], BytesIO(profile_bytes),
                                   user["color"], user["bg"])

            await ctx.send(file=discord.File(fp=buffer, filename="rank_card.png"))
        else:
            await ctx.send("Member hasn't received xp yet.")

    @profile.command(pass_context=True, name="color", aliases=["colour"])
    async def profile_color(self, ctx, *, color: discord.Color):
        """Change the highlight color used of your rank card."""
        member = str(ctx.author.id)
        guild = str(ctx.guild.id)
        async with ctx.typing():
            self.bot.db.row_factory = aiosqlite.Row
            async with self.bot.db.execute("SELECT user_id, guild_id, color "
                                           "FROM users WHERE user_id=:user AND guild_id=:guild",
                                           {"user": member, "guild": guild}) as cursor:
                await cursor.execute("UPDATE users SET color=:color WHERE user_id=:user AND guild_id=:guild",
                                     {"color": f"{color.value:0>6x}", "user": member, "guild": guild})
                await self.bot.db.commit()

        embed = discord.Embed(color=color, title=f"Changed your color to `{color}`")
        await ctx.send(embed=embed)

    @profile.command(pass_context=True, name="background", aliases=["bg"])
    async def profile_background(self, ctx, image: str = None):
        """Changes the background image of your rank card. Change image to "default" to reset your background image."""
        available_bgs = []

        for file in listdir("/opt/discord-v2/github/minesoc/backgrounds"):
            available_bgs.append(str(file[:-4]))

        if image not in available_bgs and image != "default" or image is None:
            return await ctx.send(f"List of available backgrounds:\n```{', '.join(available_bgs)}```")

        member = str(ctx.author.id)
        guild = str(ctx.guild.id)

        async with self.bot.db.execute("SELECT user_id, guild_id, bg FROM users "
                                       "WHERE user_id=:user AND guild_id=:guild",
                                       {"user": member, "guild": guild, "bg": image}) as cursor:
            await cursor.execute("UPDATE users SET bg=:bg WHERE user_id=:user AND guild_id=:guild",
                                 {"bg": image, "user": member, "guild": guild})
            await self.bot.db.commit()

        await ctx.send(embed=discord.Embed(title=f"Changed your image to `{image}`" if image != "default" else
                       "Reset your profile background."))

    @commands.command(pass_context=True, aliases=["lb", "ranks", "levels"])
    async def leaderboard(self, ctx):
        """Shows the top 10 users of your guild."""
        guild_check = ctx.guild is not None
        if guild_check:
            guild_id = str(ctx.guild.id)

            self.bot.db.row_factory = aiosqlite.Row
            async with self.bot.db.execute("SELECT user_id, guild_id, xp, lvl "
                                           "FROM users WHERE guild_id=:guild ORDER BY xp DESC",
                                           {"guild": guild_id}) as cursor:
                users = await cursor.fetchall()

            users_list = [dict(row) for row in users if not None]

            user_info = ""
            user_name = ""
            rankings = ""
            for idx, val in zip(range(10), users_list):
                user = self.bot.get_user(val["user_id"])
                if user:
                    rank = idx + 1
                    if rank == 1:
                        rank = "🥇\n"
                        top_user = f"Top Member: 🏆 **{user.name}**"
                    elif rank == 2:
                        rank = "🥈\n"
                    elif rank == 3:
                        rank = "🥉\n"
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

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def level_persistence(self, ctx):
        with open("config.json", "r") as f:
            response = json.load(f)

        print(response)

        try:
            data = response[str(ctx.guild.id)]
        except KeyError:
            response[str(ctx.guild.id)] = {"disabled_commands": [], "lvl_msg": True, "lvl_system": True}

        data = response[str(ctx.guild.id)]

        options = ["Edit persistence settings", "Edit level-up message settings"]
        options = [f"[{idx + 1}] {val}\n" for idx, val in enumerate(options)]
        responses = ["1", "2", "exit"]
        embed = discord.Embed(title=f"{ctx.guild.name} Persistence Settings",
                              description=f"```py\nUsers gain {self.bot.xp_values.min}-{self.bot.xp_values.max} XP per message\n"
                                          f"XP gain on this server is {'Enabled' if data['lvl_system'] else 'Disabled'}\n"
                                          f"Level-Up messages on this server are {'Enabled' if data['lvl_msg'] else 'Disabled'}\n\n"
                                          f"{''.join(options)}\n"
                                          f"Type the appropriate number to access the menu.\nType 'exit' to leave the menu```")

        menu = await ctx.send(embed=embed)

        def check(author):
            def inner_check(message):
                if message.author != author:
                    return False
                if message.content in responses:
                    return True
                else:
                    return False
            return inner_check

        try:
            message = await self.bot.wait_for("message", check=check(ctx.author), timeout=30)
        except asyncio.TimeoutError:
            await menu.delete()
            await ctx.error(description="Action cancelled! You took too long.")
        else:
            await menu.delete()
            await message.add_reaction(self.bot.emojis.greenTick)
            if message.content == responses[0]:
                options = ["Enable level system", "Disable level system"]
                options = [f"[{idx + 1}] {val}\n" for idx, val in enumerate(options)]
                embed = discord.Embed(title=f"Edit Persistence Settings",
                                      description=f"```py\n{''.join(options)}```\nType the appropriate number to access the menu.\nType 'exit' to leave the menu")
                menu = await ctx.send(embed=embed)
                try:
                    message = await self.bot.wait_for("message", check=check(ctx.author), timeout=30)
                except asyncio.TimeoutError:
                    await menu.delete()
                    await ctx.error(description="Action cancelled! You took too long.")
                else:
                    await message.add_reaction(self.bot.emojis.greenTick)
                    if message.content == responses[0]:
                        data["lvl_system"] = True
                    elif message.content == responses[1]:
                        data["lvl_system"] = False

                    await menu.delete()
            elif message.content == responses[1]:
                options = ["Enable level-up messages", "Disable level-up messages"]
                options = [f"[{idx + 1}] {val}\n" for idx, val in enumerate(options)]
                embed = discord.Embed(title=f"Edit Level-Up message Settings",
                                      description=f"```py\n{''.join(options)}```\nType the appropriate number to access the menu.\nType 'exit' to leave the menu")
                menu = await ctx.send(embed=embed)
                try:
                    message = await self.bot.wait_for("message", check=check(ctx.author), timeout=30)
                except asyncio.TimeoutError:
                    await menu.delete()
                    await ctx.error(description="Action cancelled! You took too long.")
                else:
                    await message.add_reaction(self.bot.emojis.greenTick)
                    if message.content == responses[0]:
                        data["lvl_msg"] = True
                    elif message.content == responses[1]:
                        data["lvl_msg"] = False

                    await menu.delete()

        print(data)
        with open("config.json", "w") as f:
            json.dump(response, f, indent=4)

    @profile_color.error
    async def color_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send("That's not a valid color! Try a hex value (e.g #FF0000) or Discord color (e.g blurple).")


def setup(bot):
    bot.add_cog(Levels(bot))
