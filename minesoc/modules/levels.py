# levels.py
# This extension handles level ups
import aiohttp.client
import discord
import time

from io import BytesIO
from discord.ext import commands
from minesoc.utils import images

CD = 120


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

    @commands.Cog.listener()
    async def on_message(self, message):
        ctx = await self.bot.get_context(message)

        guild = message.guild.id
        author = message.author.id

        await self.bot.db.execute("INSERT INTO persistence (guild, lvl_msg, lvls) VALUES ($1, TRUE, TRUE) "
                                  "ON CONFLICT (guild) DO NOTHING", guild)
        await self.bot.db.execute("INSERT INTO inventory (user_id, items) VALUES ($1, ARRAY[]::int[]) "
                                  "ON CONFLICT (user_id) DO NOTHING", author)

        if message.author.bot or ctx.valid:
            return

        config = await self.bot.db.fetchrow("SELECT * FROM persistence WHERE guild=$1", guild)
        if config["lvls"]:
            xp = self.bot.xp_gain()
            await self.bot.db.execute("INSERT INTO levels (user_id, guild_id, xp, lvl, cd, color, bg) "
                                      "VALUES ($1, $2, $3, 1, $4, $5, 'default') ON CONFLICT (user_id, guild_id) "
                                      "DO NOTHING", author, guild, xp, time.time(), 0xFFFFFF)
            user = await self.bot.db.fetchrow("SELECT * FROM levels WHERE user_id=$1 AND guild_id=$2", author, guild)

            if time.time() - user["cd"] > CD:
                await self.bot.db.execute("UPDATE levels SET xp = $1, cd= $2 WHERE user_id = $3 AND guild_id = $4",
                                          user["xp"] + xp, time.time(), author, guild)

                if user["xp"] + xp >= round((4 * (user["lvl"] ** 3) / 5)):
                    await self.bot.db.execute("UPDATE levels SET lvl = $1 WHERE user_id = $2 AND guild_id = $3",
                                              user["lvl"] + 1, author, guild)
                    if config["lvl_msg"]:
                        await ctx.send(f"🆙 | **{message.author.name}** is now **Level {user['lvl'] + 1}**")

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
            guild = ctx.guild.id

            user = await self.bot.db.fetchrow("SELECT * FROM levels WHERE user_id=$1 AND guild_id=$2", member_id, guild)
            if user:
                async with ctx.typing(), aiohttp.ClientSession() as session:
                    async with session.get(f"{member.avatar_url}") as r:
                        profile_bytes = await r.read()

                color = discord.Color(user["color"]).to_rgb()
                buffer = profile.draw(member.name, user["lvl"], user["xp"], BytesIO(profile_bytes), color, user["bg"])

                await ctx.send(file=discord.File(fp=buffer, filename="card.png"))
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
        guild = ctx.guild.id
        users = await self.bot.db.fetch("SELECT * FROM levels WHERE guild_id=$1 ORDER BY xp DESC", guild)

        ranks = {(y := x + 1): f"#{y}" if y > 3 else f"{self.leaderboard_emojis[y]}" for x in range(10)}
        fields = {"member": [], "level": [], "rank": []}

        for index, value in zip(range(10), users):
            user = self.bot.get_user(value["user_id"])
            if user:
                if (rank := index + 1) == 1:
                    top_user = f"Top Member: 🏆 **{str(user)}**"
                fields["rank"].append(ranks[rank])
                fields["member"].append(f"**{user.name}**")
                xp = round((4 * (value['lvl'] ** 3) / 5))
                fields["level"].append(f"Level {value['lvl']} ({value['xp']}/{xp})")
        else:
            for value in fields.values():
                value.append("...")

        leaderboard = discord.Embed(color=ctx.me.colour, title=f"Top 10 in {ctx.guild.name}", description=top_user,
                                    timestamp=ctx.message.created_at)
        leaderboard.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)

        author = await self.bot.db.fetchrow("SELECT * FROM levels WHERE user_id=$1 AND guild_id=$2",
                                            ctx.author.id, guild)

        if author:
            fields["rank"].append(ranks[users.index(author) + 1])
            fields["member"].append(f"**{ctx.author.name}**")
            xp = round((4 * (author['lvl'] ** 3) / 5))
            fields["level"].append(f"Level {author['lvl']} ({author['xp']}/{xp})")

        leaderboard.add_field(name="Rank", value="\n".join(fields["rank"]), inline=True)
        leaderboard.add_field(name="Member", value="\n".join(fields["member"]), inline=True)
        leaderboard.add_field(name="Level", value="\n".join(fields["level"]), inline=True)

        await ctx.send(embed=leaderboard)

    @profile_color.error
    async def color_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send("That's not a valid color! Try a hex value (e.g #FF0000) or a Discord color (e.g blurple).")


def setup(bot):
    bot.add_cog(Levels(bot))
