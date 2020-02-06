import discord
import re
import aiohttp
import aiosqlite

from discord.ext import commands
from minesoc.utils import errors
from datetime import datetime
from libneko import pag


@pag.embed_generator(max_chars=2048, provides_numbering=False)
def tags_factory(paginator, page, page_index):
    return discord.Embed(color=discord.Color.blurple(), description=page,
                         title="🔖 Tag List").set_footer(text=f"Page {page_index + 1} / {len(paginator)}")


class Tags(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.name_limit = 20
        self.content_limit = 2000
        self.url_regex = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
        self.leaderboard_emojis = {"1": "🥇", "2": "🥈", "3": "🥉"}

        self.bot.loop.create_task(self.create_table())

    async def cog_check(self, ctx):
        if not ctx.guild:
            raise commands.NoPrivateMessage
        else:
            return True

    async def create_table(self):
        await self.bot.wait_until_ready()

        query = "CREATE TABLE IF NOT EXISTS tags(guild integer NOT NULL, name text NOT NULL, owner integer NOT NULL, " \
                "content text NOT NULL, usages integer DEFAULT 0, creation_date text NOT NULL)"

        await self.bot.db.execute(query)

    async def get_tag(self, ctx: commands.Context, name):
        cur = await self.bot.db.execute("SELECT * FROM tags WHERE guild=:guild AND name=:name",
                                        {"guild": ctx.guild.id, "name": name})
        tag = await cur.fetchone()
        if tag:
            return tag

    async def create_tag(self, ctx: commands.Context, name, content):
        conn = self.bot.db
        return bool(await conn.execute("INSERT INTO tags(name, content, guild, owner, creation_date) VALUES (:name, :content, :guild, :owner, datetime('now'))",
                                       {"name": name, "content": content,
                                        "guild": ctx.guild.id, "owner": ctx.author.id}))

    async def edit_tag(self, ctx: commands.Context, name, new_content):
        conn = self.bot.db
        return bool(await conn.execute("UPDATE tags SET content=:content name=:name AND guild=:guild AND owner=:owner",
                                       {"content": new_content, "name": name,
                                        "guild": ctx.guild.id, "owner": ctx.author.id}))

    async def rename_tag(self, ctx: commands.Context, name, new_name):
        conn = self.bot.db
        return bool(await conn.execute("UPDATE tags SET name=:new_name WHERE name=:name AND guild=:guild AND owner=:owner",
                                       {"new_name": new_name, "name": name,
                                        "guild": ctx.guild.id, "owner": ctx.author.id}))

    async def delete_tag(self, ctx: commands.Context, name):
        async with self.bot.db.execute("SELECT * FROM tags WHERE name=:name AND guild=:guild AND owner=:owner",
                                       {"name": name, "guild": ctx.guild.id, "owner": ctx.author.id}) as c:
            await c.execute("DELETE FROM tags WHERE name=:name AND guild=:guild AND owner=:owner",
                            {"name": name, "guild": ctx.guild.id, "owner": ctx.author.id})
            if c.rowcount < 1:
                return False
            return True

    async def make_image_request(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    if str(response.content_type).split("/")[0] == "image":
                        return url

        return False

    def match_url(self, maybe_url):
        return bool(re.match(self.url_regex, maybe_url))

    async def is_image(self, ctx: commands.Context, tag):
        content = tag["content"]

        for word in content.split():
            if self.match_url(word):
                image = await self.make_image_request(word)
                if image:
                    return [image, content.replace(image, "")]

        return False

    @commands.group(invoke_without_command=True)
    async def tag(self, ctx: commands.Context, *, name):
        """Tag management"""
        tag = await self.get_tag(ctx, name)
        if tag:
            image = await self.is_image(ctx, tag)
            if image:
                if isinstance(image, list):
                    embed = discord.Embed(color=self.bot.colors.neutral, description=image[1] if image[1] else None,
                                          timestamp=datetime.strptime(tag["creation_date"], "%Y-%m-%d %H:%M:%S"))
                    embed.set_image(url=image[0])
                    embed.set_footer(text="Created at:")
                    await ctx.send(embed=embed)
                else:
                    embed = discord.Embed(color=self.bot.colors.neutral,
                                          timestamp=datetime.strptime(tag["creation_date"], "%Y-%m-%d %H:%M:%S"))
                    embed.set_image(url=image)
                    embed.set_footer(text="Created at:")
                    await ctx.send(embed=embed)
            else:
                embed = discord.Embed(color=self.bot.colors.neutral, description=tag["content"],
                                      timestamp=datetime.strptime(tag["creation_date"], "%Y-%m-%d %H:%M:%S"))
                embed.set_footer(text="Created at:")
                await ctx.send(embed=embed)

            self.bot.db.row_factory = aiosqlite.Row
            cur = await self.bot.db.execute("SELECT usages FROM tags WHERE name=:name AND guild=:guild",
                                            {"name": name, "guild": ctx.guild.id})
            usages = await cur.fetchone()

            await self.bot.db.execute("UPDATE tags SET usages=:usages WHERE name=:name AND guild=:guild",
                                      {"usages": usages["usages"] + 1, "name": name, "guild": ctx.guild.id})
            await self.bot.db.commit()
        else:
            await ctx.error(description=f"Tag `{name}` can't be found")

    @tag.command(name="raw")
    async def tag_raw(self, ctx: commands.Context, *, name):
        """Post a tag with escaped markdown"""
        tag = await self.get_tag(ctx, name)
        await ctx.send(discord.utils.escape_markdown(tag["content"]))

    @tag.command(name="create")
    async def tag_create(self, ctx: commands.Context, name: str, *, content: str):
        """Create a tag"""
        if len(name) > self.name_limit:
            await ctx.error(description=f"The provided name is too long! Maximum is `{self.name_limit}`.")
        elif len(content) > self.content_limit:
            await ctx.error(description=f"The provided content is too long! Maximum is `{self.content_limit}`.")
        elif name in list(command.name for command in self.walk_commands()):
            await ctx.error(description=f"`{name}` is a reserved keyword.")
        else:
            if await self.create_tag(ctx, name, content):
                await ctx.message.add_reaction(self.bot.emojis.greenTick)
            else:
                await ctx.error(description="The tag can't be created because it already exists.")

    @tag.command(name="edit")
    async def tag_edit(self, ctx: commands.Context, name: str, *, new_content: str):
        """Edit the content of a already existing tag"""
        if len(new_content) > self.content_limit:
            await ctx.error(description=f"The provided content is too long! Maximum is `{self.content_limit}`.")
        else:
            if await self.edit_tag(ctx, name, new_content):
                await ctx.message.add_reaction(self.bot.emojis.greenTick)
            else:
                await ctx.error(description="The tag can't be edited because ... .")

    @tag.command(name="rename")
    async def tag_rename(self, ctx: commands.Context, name: str, *, new_name: str):
        """Edit the name of a already existing tag"""
        if len(new_name) > self.name_limit:
            await ctx.error(description=f"The provided content is too long! Maximum is `{self.name_limit}`.")
        else:
            if await self.rename_tag(ctx, name, new_name):
                await ctx.message.add_reaction(self.bot.emojis.greenTick)
            else:
                await ctx.error(description="The tag can't be renamed because the new name does already exist.")

    @tag.command(name="delete")
    async def tag_delete(self, ctx: commands.Context, *, name: str):
        """Delete a tag"""
        if await self.delete_tag(ctx, name):
            await ctx.message.add_reaction(self.bot.emojis.greenTick)
        else:
            await ctx.error(
                description="The tag can't be deleted. Either this tag doesn't exist, or you're not the owner of it.")

    @tag.command(name="list")
    async def tag_list(self, ctx: commands.Context, member: discord.Member = None):
        """Shows a list of all tags you own"""
        member = member or ctx.author
        self.bot.db.row_factory = aiosqlite.Row
        cur = await self.bot.db.execute("SELECT name FROM tags WHERE guild=:guild AND owner=:owner",
                                        {"guild": ctx.guild.id, "owner": member.id})
        tags = await cur.fetchall()
        tags = [dict(row) for row in tags]

        if tags:
            nav = pag.EmbedNavigatorFactory(max_lines=15, factory=tags_factory)
            for index, tag in enumerate(tags):
                nav.add_line(f"{index + 1}. {tag.get('name')}")
            else:
                nav.start(ctx)
        else:
            print("NO TAGS")
            if member == ctx.author:
                await ctx.info("You don't have any tags.")
            else:
                await ctx.info(f"{member.mention} doesn't have any tags.")

    @tag.command(name="all")
    async def tag_all(self, ctx: commands.Context):
        """Shows all tags from the current guild / server"""
        cur = await self.bot.db.execute("SELECT name FROM tags WHERE guild=:guild", {"guild": ctx.guild.id})
        tags = await cur.fetchone()
        if tags:
            nav = pag.EmbedNavigatorFactory(max_lines=15, factory=tags_factory)
            for index, tag in enumerate(tags):
                nav.add_line(f"{index + 1}. {tag.get('name')}")
            else:
                nav.start(ctx)
        else:
            await ctx.error(
                description=f"This {'guild' if ctx.invoked_with == 'guild' else 'server'} doesn't have tags.")

    @tag.command(name="leaderboard", aliases=["lb"])
    async def tag_leaderboard(self, ctx: commands.Context):
        """Shows a leaderboard for all tags on the current server. Sorted by usages"""
        leaderboard_string_usages = str()
        leaderboard_string_date = str()

        cur1 = await self.bot.db.execute("SELECT name, usages, owner FROM tags WHERE guild=:guild ORDER BY usages DESC LIMIT 3",
                                         {"guild": ctx.guild.id})
        tags_by_usages = await cur1.fetchall()
        tags_by_usages = [dict(row) for row in tags_by_usages]
        cur2 = await self.bot.db.execute("SELECT name, creation_date, owner FROM tags WHERE guild=:guild ORDER BY creation_date ASC LIMIT 3",
                                         {"guild": ctx.guild.id})
        tags_by_date = await cur2.fetchall()
        tags_by_date = [dict(row) for row in tags_by_date]

        if tags_by_usages and tags_by_date:
            try:
                for index, tag_by_usages in enumerate(tags_by_usages):
                    member = discord.utils.get(ctx.guild.members, id=tag_by_usages.get('owner'))
                    usages = tag_by_usages.get('usages')
                    leaderboard_string_usages += f"{self.leaderboard_emojis[str(index + 1)]} " \
                                                 f"**{tag_by_usages.get('name')}** from " \
                                                 f"{member.mention if member else 'Left Member'} " \
                                                 f"with `{usages}` {'usages' if usages > 1 else 'usage'}.\n"

                for index, tag_by_date in enumerate(tags_by_date):
                    member = discord.utils.get(ctx.guild.members, id=tag_by_date.get('owner'))
                    leaderboard_string_date += f"{self.leaderboard_emojis[str(index + 1)]} " \
                                               f"**{tag_by_date.get('name')}** from " \
                                               f"{member.mention if member else '*Member left*'} " \
                                               f"created on `{tag_by_date.get('creation_date')}`.\n"
            finally:
                embed = discord.Embed(color=self.bot.colors.neutral)
                embed.set_author(name=f"📋 {ctx.guild.name}'s Leaderboard",
                                 icon_url=ctx.guild.icon_url_as(format="png"))
                embed.add_field(name="Usages", value=leaderboard_string_usages, inline=False)
                embed.add_field(name="Date", value=leaderboard_string_date, inline=False)
                await ctx.send(embed=embed)
        else:
            await ctx.error(description="This server has no tags.")


def setup(bot):
    bot.add_cog(Tags(bot))

