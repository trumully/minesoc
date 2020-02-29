import typing

import discord
import asyncpg
from discord.ext import commands


class Owner(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_check(self, ctx):
        if not await self.bot.is_owner(ctx.author):
            raise commands.NotOwner
        else:
            return True

    async def add_blacklist(self, id, table, reason):
        if table == "user_blacklist":
            await self.bot.db.execute("INSERT INTO user_blacklist (id, reason) VALUES ($1, $2)", id, reason)
        else:
            await self.bot.db.execute("INSERT INTO guild_blacklist (id, reason) VALUES ($1, $2)", id, reason)

    async def remove_blacklist(self, id, table):
        if table == "user_blacklist":
            await self.bot.db.execute("DELETE FROM user_blacklist WHERE id=$1", id)
        else:
            await self.bot.db.execute("DELETE FROM guild_blacklist WHERE id=$1", id)

    async def get_blacklist_entry(self, id, table):
        if table == "user_blacklist":
            b = await self.bot.db.fetchrow("SELECT * FROM user_blacklist WHERE id=$1", id)
        else:
            b = await self.bot.db.fetchrow("SELECT * FROM guild_blacklist WHERE id=$1", id)
        return b

    @commands.command()
    async def load(self, ctx, module: str):
        """Load a module"""
        try:
            self.bot.load_extension(f"minesoc.{self.bot.config.modules_path}.{module}")
        except commands.ExtensionNotFound:
            return await ctx.error(description=f"Module `{module}` not found.")
        except commands.ExtensionAlreadyLoaded:
            return await ctx.error(description=f"Module `{module}` already loaded.")
        except Exception as ex:
            self.bot.logger.error(ex, exc_info=ex)
            return await ctx.error(
                description=f"Module `{module}` failed to load. Check the logs for detailed information.")
        else:
            return await ctx.success(description=f"Module `{module}` has been loaded successfully.")

    @commands.command()
    async def unload(self, ctx, module: str):
        """Unload a module"""
        try:
            self.bot.unload_extension(f"minesoc.{self.bot.config.modules_path}.{module}")
        except commands.ExtensionNotFound:
            return await ctx.error(description=f"Module `{module}` not found.")
        else:
            return await ctx.success(description=f"Module `{module}` has been unloaded successfully.")

    @commands.command()
    async def reload(self, ctx, module: str):
        """Reload a module"""
        try:
            self.bot.reload_extension(f"minesoc.{self.bot.config.modules_path}.{module}")
        except commands.ExtensionNotFound:
            return await ctx.error(description=f"Module `{module}` not found.")
        except Exception as ex:
            self.bot.logger.error(ex, exc_info=ex)
            return await ctx.error(
                description=f"Module `{module}` failed to reload. Check the logs for detailed information.")
        else:
            return await ctx.success(description=f"Module `{module}` has been reloaded successfully.")

    @commands.command(aliases=["sd", "logout"])
    async def shutdown(self, ctx: commands.Context):
        """Stops the bot, should restart it"""
        try:
            await self.bot.logout()
            await self.bot.close()
        except Exception as ex:
            await self.bot.logger.warning("An error occurred trying to logout", exc_info=ex)
        else:
            await ctx.message.add_reaction("👌")

    @commands.group(invoke_without_command=True)
    async def blacklist(self, ctx: commands.Context):
        """Punish naughty people"""
        await ctx.send_help(ctx.command)

    @blacklist.command(name="add")
    async def blacklist_add(self, ctx: commands.Context, target: typing.Union[discord.User, discord.Guild], *,
                            reason: str = "No reason given."):
        """Add a guild or user to the blacklist"""
        table = "user_blacklist" if isinstance(target, discord.User) else "guild_blacklist"

        if target not in self.bot.user_blacklist and target not in self.bot.guild_blacklist:
            await self.add_blacklist(target.id, table, reason)
            await ctx.message.add_reaction(self.bot.custom_emojis.green_tick)
        else:
            await ctx.error(description=f"{table.split('_')[0].title()} is already blacklisted.")

    @blacklist.command(name="remove")
    async def blacklist_remove(self, ctx: commands.Context, target: typing.Union[discord.User, discord.Guild]):
        """Remove a guild or user from the blacklist"""
        table = "user_blacklist" if isinstance(target, discord.User) else "guild_blacklist"

        if target in self.bot.user_blacklist or target in self.bot.guild_blacklist:
            await self.remove_blacklist(target.id, table)
            await ctx.message.add_reaction(self.bot.custom_emojis.green_tick)
        else:
            await ctx.error(description=f"{table.split('_')[0].title()} is not blacklisted.")

    @blacklist.command(name="refresh")
    async def blacklist_refresh(self, ctx):
        try:
            self.user_blacklist = [u["id"] for u in (await self.bot.db.fetch("SELECT id FROM user_blacklist"))]
            self.guild_blacklist = [g["id"] for g in (await self.bot.db.fetch("SELECT id FROM guild_blacklist"))]
            await ctx.message.add_reaction(self.bot.emojis.green_tick)
        except Exception as e:
            await ctx.message.add_reaction(self.bot.emojis.red_tick)
            self.bot.logger.error("Blacklist could not be refreshed.", exc_info=e)

    @blacklist.command(name="show")
    async def blacklist_show(self, ctx: commands.Context, target: typing.Union[discord.User, discord.Guild]):
        """Show a entry from the blacklist"""
        table = "user_blacklist" if isinstance(target, discord.User) else "guild_blacklist"

        if target in self.bot.user_blacklist or target in self.bot.guild_blacklist:
            entry = await self.get_blacklist_entry(target.id, table)
            embed = discord.Embed(color=self.bot.colors.neutral)
            if isinstance(target, discord.User):
                u = discord.utils.get(self.bot.users, id=target.id)
                if u:
                    embed.set_author(name=f"User {u} ({u.id})", icon_url=u.avatar_url_as(static_format="png"))
                else:
                    embed.set_author(name=f"User {u.id}")
            else:
                g = discord.utils.get(self.bot.guilds, id=target.id)
                if g:
                    embed.set_author(name=f"Guild {g} ({g.id})", icon_url=g.icon_url_as(static_format="png"))
                else:
                    embed.set_author(name=f"Guild {g.id}")
            embed.add_field(name="Reason:", value=entry['reason'])
            await ctx.send(embed=embed)
        else:
            await ctx.error(description=f"{table.split('_')[0].title()} is not blacklisted.")


def setup(bot):
    bot.add_cog(Owner(bot))
