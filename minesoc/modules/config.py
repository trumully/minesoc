# config.py
# This extension handles certain bot configurations.
import asyncio
import asyncpg

import discord
from discord.ext import commands

from minesoc.utils import checks


class PrefixTooLong(commands.CommandError):
    pass


class Config(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.command_prefix = self.determine_prefix
        self.prefix_limit = 15

        self.bot.loop.create_task(self.create_prefix_table())
        self.bot.loop.create_task(self.create_persistence_table())

    async def determine_prefix(self, bot, message):
        if not message.guild:
            return self.bot.config.default_prefix

        async with self.bot.db.acquire() as conn:
            prefix = await self._fetch_prefix(message.guild.id)
            if prefix:
                if prefix["mention"]:
                    return commands.when_mentioned_or(prefix["value"])(bot, message)
                else:
                    return prefix["value"]
            else:
                return self.bot.config.default_prefix

    async def create_prefix_table(self):
        await self.bot.wait_until_ready()

        query = "CREATE TABLE IF NOT EXISTS prefix(guild bigint UNIQUE NOT NULL, value text NOT NULL, mention bool " \
                "DEFAULT FALSE) "

        await self.bot.db.execute(query)

    async def create_persistence_table(self):
        await self.bot.wait_until_ready()

        query = "CREATE TABLE IF NOT EXISTS persistence(guild bigint UNIQUE NOT NULL, lvl_msg bool DEFAULT TRUE, " \
                "lvls bool DEFAULT TRUE) "

        await self.bot.db.execute(query)

    async def _fetch_prefix(self, guild: int):
        async with self.bot.db.acquire() as conn:
            return await conn.fetchrow("SELECT value, mention FROM prefix WHERE guild=$1", guild)

    async def _set_prefix(self, guild: int, prefix: str):
        if len(prefix) > self.prefix_limit:
            raise PrefixTooLong

        async with self.bot.db.acquire() as conn:
            await conn.execute(
                "INSERT INTO prefix (guild, value) VALUES ($1, $2) ON CONFLICT (guild) DO UPDATE SET "
                "value=EXCLUDED.value WHERE EXCLUDED.guild=$1", guild, prefix)

    async def _set_prefix_mentionable(self, guild: int, boolean: bool):
        async with self.bot.db.acquire() as conn:
            await conn.execute(
                "INSERT INTO prefix (guild, value) VALUES ($1, $2) ON CONFLICT (guild) DO UPDATE SET mention=$3 WHERE "
                "EXCLUDED.guild=$1", guild, self.bot.config.default_prefix, boolean)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.content in [f"<@!{self.bot.user.id}>", f"<@{self.bot.user.id}>"]:
            prefix = await self._fetch_prefix(message.guild.id)
            await message.channel.send(f"Hello {message.author.mention}!\nMy prefix is `{prefix.value}`")

    @commands.group(invoke_without_command=True)
    async def prefix(self, ctx: commands.Context):
        """Configure the guild's prefix"""
        prefix = await self._fetch_prefix(ctx.guild.id)
        p = self.bot.config.default_prefix
        m = False
        if prefix:
            p = prefix["value"]
            if prefix["mention"]:
                m = True

        embed = discord.Embed(color=self.bot.colors.neutral)
        embed.set_author(name=str(ctx.guild.me), icon_url=self.bot.user.avatar_url_as(format="png"))
        embed.add_field(name="Value", value=p)
        embed.add_field(name="Mentionable", value=self.bot.custom_emojis.on if m else self.bot.custom_emojis.off)
        embed.set_footer(text=f"Your prefix can be up to {self.prefix_limit} characters long")

        await ctx.send(embed=embed)

    @prefix.command(name="set")
    @checks.is_owner_or_has_permissions(manage_guild=True)
    async def prefix_set(self, ctx: commands.Context, *, prefix: str):
        """Change the prefix"""
        if prefix != self.bot.config.default_prefix:
            await self._set_prefix(ctx.guild.id, prefix)
            await ctx.success(description=f"Successfully updated prefix to: `{prefix}`")
        else:
            await ctx.error(description=f"Can't set the prefix to `{prefix}` because it's already the default one.")

    @prefix.command(name="reset")
    @checks.is_owner_or_has_permissions(manage_guild=True)
    async def prefix_reset(self, ctx: commands.Context):
        """Reset the prefix to the default one"""
        if ctx.prefix != self.bot.config.default_prefix:
            await self._set_prefix(ctx.guild.id, self.bot.config.default_prefix)
            await ctx.success(description=f"Successfully reset prefix to `{self.bot.config.default_prefix}`")
        else:
            await ctx.error(
                description=f"The bots prefix is already the default one. (`{self.bot.config.default_prefix}`)")

    @prefix.command(name="mention")
    @checks.is_owner_or_has_permissions(manage_guild=True)
    async def prefix_mention(self, ctx: commands.Context):
        """Allow the bots mention to be used as prefix"""
        prefix = await self._fetch_prefix(ctx.guild.id)
        mention = True
        if prefix:
            if prefix["mention"]:
                mention = False

        await self._set_prefix_mentionable(ctx.guild.id, mention)
        await ctx.success(description=f"Mentionable prefix {'enabled' if mention else 'disabled'}.")

    @commands.command()
    @checks.is_owner_or_has_permissions(manage_guild=True)
    async def persistence(self, ctx):
        """Modify level related-systems of your guild."""
        guild = ctx.guild.id
        config = await self.bot.db.fetchrow("SELECT * FROM persistence WHERE guild=$1", guild)

        if not config:
            await self.bot.db.execute("INSERT INTO persistence(guild, lvl_msg, lvls) VALUES($1, TRUE, TRUE)", guild)
            config = await self.bot.db.fetchrow("SELECT * FROM persistence WHERE guild=$1", guild)

        do_msg = config["lvl_msg"]
        do_lvl = config["lvls"]

        check = {True: "Enabled", False: "Disabled"}
        title = f"{ctx.guild.name} Persistence Settings"
        options = {"1": "Edit persistence settings", "2": "Edit level-up message settings"}
        extras = f"Users gain {self.bot.xp_values.min}-{self.bot.xp_values.max} XP per message\n"\
                 f"XP gain on this server is {check[do_lvl]}\nLevel-Up messages on this server are {check[do_msg]}"

        menu = await ctx.menu(title=title, options=options, extras=extras)

        if menu:
            if menu == "1":
                options = {"1": "Enable level system", "2": "Disable level system"}
                title = "Edit Persistence Settings"
            else:
                options = {"1": "Enable level-up messages", "2": "Disable level-up messages"}
                title = "Edit Level-Up message Settings"
            sub_menu = await ctx.menu(title=title, options=options)
            if sub_menu:
                if title == "Edit Persistence Settings":
                    if sub_menu == "1":
                        await self.bot.db.execute("UPDATE persistence SET lvls=TRUE WHERE guild=$1", guild)
                        await ctx.success(f"**{ctx.author.name}**, you enabled the level system.")
                    else:
                        await self.bot.db.execute("UPDATE persistence SET lvls=FALSE WHERE guild=$1", guild)
                        await ctx.success(f"**{ctx.author.name}**, you disabled the level system.")
                else:
                    if sub_menu == "1":
                        await self.bot.db.execute("UPDATE persistence SET lvl_msg=TRUE WHERE guild=$1", guild)
                        await ctx.success(f"**{ctx.author.name}**, you enabled level-up messages.")
                    else:
                        await self.bot.db.execute("UPDATE persistence SET lvl_msg=FALSE WHERE guild=$1", guild)
                        await ctx.success(f"**{ctx.author.name}**, you disabled level-up messages.")

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, PrefixTooLong):
            desc = f"The provided prefix is too long! It can't be longer than `{self.prefix_limit}` characters."
            await ctx.error(description=desc)

    def cog_unload(self):
        self.bot.command_prefix = self.bot.config.default_prefix


def setup(bot):
    bot.add_cog(Config(bot))
