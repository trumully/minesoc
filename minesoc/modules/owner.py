import discord

from discord.ext import commands
from datetime import datetime
from minesoc.utils import emojis, logger


class Owner(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_check(self, ctx):
        if not await self.bot.is_owner(ctx.author):
            raise commands.NotOwner
        else:
            return True

    @commands.command()
    async def load(self, ctx, module: str):
        """Load a module"""
        try:
            self.bot.load_extension(f"minesoc.{self.bot.config.MODULES_PATH}.{module}")
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
            self.bot.unload_extension(f"minesoc.{self.bot.config.MODULES_PATH}.{module}")
        except commands.ExtensionNotFound:
            return await ctx.error(description=f"Module `{module}` not found.")
        else:
            return await ctx.success(description=f"Module `{module}` has been unloaded successfully.")

    @commands.command()
    async def reload(self, ctx, module: str):
        """Reload a module"""
        try:
            self.bot.reload_extension(f"minesoc.{self.bot.config.MODULES_PATH}.{module}")
        except commands.ExtensionNotFound:
            return await ctx.error(description=f"Module `{module}` not found.")
        except Exception as ex:
            self.bot.logger.error(ex, exc_info=ex)
            return await ctx.error(
                description=f"Module `{module}` failed to reload. Check the logs for detailed information.")
        else:
            return await ctx.success(description=f"Module `{module}` has been reloaded successfully.")

    @commands.command(aliases=["kys"])
    async def shutdown(self, ctx: commands.Context):
        """Stops the bot, should restart it"""
        await ctx.message.add_reaction("👌")
        try:
            await self.bot.logout()
            await self.bot.close()
        except Exception as ex:
            await self.bot.logger.warning("An error occurred trying to logout", exc_info=ex)

    @commands.command()
    async def emojirefresh(self, ctx):
        _emojis = emojis.CustomEmojis()
        try:
            _emojis.fetch_emojis(self.bot.dev_guild)
            _emojis.reinit()
        except Exception as err:
            await ctx.send(err)


def setup(bot):
    bot.add_cog(Owner(bot))
