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

    async def check_user(self, id, table):
        if table == "user_blacklist":
            return await self.bot.db.fetchrow("SELECT EXISTS(SELECT 1 FROM user_blacklist WHERE id=$1)", id)
        else:
            return await self.bot.db.fetchrow("SELECT EXISTS(SELECT 1 FROM guild_blacklist WHERE id=$1)", id)

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
            return await self.bot.db.fetchrow("SELECT * FROM user_blacklist WHERE id=$1", id)
        else:
            return await self.bot.db.fetchrow("SELECT * FROM guild_blacklist WHERE id=$1", id)

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
    async def blacklist_add(self, ctx: commands.Context, target, *, reason: str = "No reason given."):
        """Add a guild or user to the blacklist"""
        table = "user_blacklist" if isinstance(target, discord.User) else "guild_blacklist"
        guild = None

        try:
            check = await self.check_user(target.id, table)
        except Exception:
            guild = discord.utils.get(self.bot.guilds, id=int(target))
            if not guild:
                return

            check = await self.check_user(int(target), table)

        if not check[0]:
            if isinstance(target, discord.User):
                await self.add_blacklist(target.id, table, reason)
            else:
                await self.add_blacklist(int(target), table, reason)

            await ctx.message.add_reaction(self.bot.custom_emojis.green_tick)
            if not isinstance(target, discord.User):
                embed = discord.Embed(color=self.bot.colors.red,
                                      description=f"Your guild / server has been blacklisted. "
                                                  f"If you wish to know the reason, join the "
                                                  f"[Support server]({self.bot.invite_url})")
                await guild.owner.send(embed=embed)
                await guild.leave()
                self.bot.logger.info(f"Added guild with ID {target} to blacklist.")
            else:
                self.bot.logger.info(f"Added user with ID {target.id} to blacklist")
        else:
            await ctx.error(description=f"{table.split('_')[0].title()} is already blacklisted.")

    @blacklist.command(name="remove")
    async def blacklist_remove(self, ctx: commands.Context, target):
        """Remove a guild or user from the blacklist"""
        table = "user_blacklist" if isinstance(target, discord.User) else "guild_blacklist"

        if isinstance(target, discord.User):
            check = await self.check_user(target.id, table)
            target = target.id
        else:
            check = await self.check_user(int(target), table)
            target = int(target)

        if check[0]:
            await self.remove_blacklist(target, table)
            await ctx.message.add_reaction(self.bot.custom_emojis.green_tick)
        else:
            await ctx.error(description=f"{table.split('_')[0].title()} is not blacklisted.")

    @blacklist.command(name="show")
    async def blacklist_show(self, ctx: commands.Context, target):
        """Show a entry from the blacklist"""
        table = "user_blacklist" if isinstance(target, discord.User) else "guild_blacklist"
        check = await self.check_user(target.id, table)

        if check[0]:
            embed = discord.Embed(color=self.bot.colors.neutral)
            if isinstance(target, discord.User):
                entry = await self.get_blacklist_entry(target.id, table)
                u = discord.utils.get(self.bot.users, id=target.id)
                if u:
                    embed.set_author(name=f"User {u} ({u.id})", icon_url=u.avatar_url_as(static_format="png"))
                else:
                    embed.set_author(name=f"User {u.id}")
            else:
                entry = await self.get_blacklist_entry(target, table)
                g = discord.utils.get(self.bot.guilds, id=target)
                if g:
                    embed.set_author(name=f"Guild {g} ({g.id})", icon_url=g.icon_url_as(static_format="png"))
                else:
                    embed.set_author(name=f"Guild {g.id}")
            embed.add_field(name="Reason:", value=entry['reason'])
            await ctx.send(embed=embed)
        else:
            await ctx.error(description=f"{table.split('_')[0].title()} is not blacklisted.")

    @blacklist.command(name="all")
    async def blacklist_show_all(self, ctx):
        user_list = await self.bot.db.fetch("SELECT * FROM user_blacklist LIMIT 25")
        guild_list = await self.bot.db.fetch("SELECT * FROM guild_blacklist LIMIT 25")

        embed = discord.Embed(title=f"{self.bot.user.name} Blacklist")

        user_value = "\n".join(str(user["id"]) for user in user_list) if user_list else "None"
        guild_value = "\n".join(str(guild["id"]) for guild in guild_list) if guild_list else "None"

        embed.add_field(name="Users", value=user_value)
        embed.add_field(name="Guilds", value=guild_value)

        await ctx.send(embed=embed)

    @commands.command()
    async def add_item(self, ctx, item_price: int, item_type: int, *, item_name: str = None):
        try:
            result = await self.bot.db.execute("INSERT INTO items (name, price, type) VALUES ($1, $2, $3)",
                                               item_name, item_price, item_type)
            await ctx.send(result)
        except Exception as ex:
            await ctx.error(description=ex)

    @commands.command()
    async def remove_item(self, ctx, item_id: int):
        try:
            result = await self.bot.db.execute("DELETE FROM items WHERE id=$1", item_id)
            await ctx.send(result)
        except Exception as ex:
            await ctx.error(description=ex)


def setup(bot):
    bot.add_cog(Owner(bot))
