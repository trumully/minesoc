# config.py
# This extension handles certain bot configurations.
import discord
import asyncio

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
            await message.channel.send(f"Hello {message.author.mention}!\nMy prefix is `{prefix}`")

    @commands.group(invoke_without_command=True)
    async def prefix(self, ctx: commands.Context):
        """Configurate the guild's prefix"""
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
        guild = ctx.guild.id
        config = await self.bot.db.fetchrow("SELECT * FROM persistence WHERE guild=$1", guild)

        do_msg = config["lvl_msg"]
        do_lvl = config["lvls"]

        options = ["Edit persistence settings", "Edit level-up message settings"]
        options = [f"[{idx + 1}] {val}\n" for idx, val in enumerate(options)]
        responses = ["1", "2", "exit"]
        embed = discord.Embed(title=f"{ctx.guild.name} Persistence Settings",
                              description=f"```py\nUsers gain {self.bot.xp_values.min}-{self.bot.xp_values.max} XP per message\n"
                                          f"XP gain on this server is {'Enabled' if do_lvl else 'Disabled'}\n"
                                          f"Level-Up messages on this server are {'Enabled' if do_msg else 'Disabled'}\n\n"
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
            await message.add_reaction(self.bot.custom_emojis.greenTick)
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
                    await message.add_reaction(self.bot.custom_emojis.greenTick)

                    if message.content == responses[0]:
                        await self.bot.db.execute("UPDATE persistence SET lvls=TRUE WHERE guild=$1", guild)
                    elif message.content == responses[1]:
                        await self.bot.db.execute("UPDATE persistence SET lvls=FALSE WHERE guild=$1", guild)

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
                    await message.add_reaction(self.bot.custom_emojis.greenTick)
                    if message.content == responses[0]:
                        await self.bot.db.execute("UPDATE persistence SET lvl_msg=TRUE WHERE guild=$1", guild)
                    elif message.content == responses[1]:
                        await self.bot.db.execute("UPDATE persistence SET lvl_msg=FALSE WHERE guild=$1", guild)

                    await menu.delete()

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, PrefixTooLong):
            await ctx.error(
                description=f"The provided prefix is too long! It can't be longer than `{self.prefix_limit}` characters.")

    def cog_unload(self):
        self.bot.command_prefix = self.bot.config.default_prefix


def setup(bot):
    bot.add_cog(Config(bot))
