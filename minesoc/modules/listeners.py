import asyncio

import discord
import asyncpg
from discord.ext import commands


class Listeners(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def bot_check(self, ctx):
        if not ctx.guild:
            return False

        if not self.bot.is_ready():
            await ctx.message.add_reaction("⏱️")
            return False

        return True

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CheckFailure):
            pass

        elif isinstance(error, commands.DisabledCommand):
            await ctx.error(description=f"`{ctx.command}` is currently disabled. Try again later.")

        elif isinstance(error, (commands.BadArgument, commands.BadUnionArgument)):
            await ctx.error(
                description=f"A parse or conversion error occurred with your arguments. Check your input and try "
                            f"again. If you need help, use `{ctx.prefix}help "
                            f"{ctx.command.qualified_name or ctx.command.name}`")

        elif isinstance(error, discord.Forbidden):
            await ctx.error(
                description="I'm unable to perform this action. "
                            "This could happen due to missing permissions for the bot.")

        elif isinstance(error, commands.NotOwner):
            await ctx.error(description="This command is only available to the bot developer.")

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.error(
                description=f"`{error.param.name}` is a required argument that is missing. For more help use "
                            f"`{ctx.prefix}help {ctx.command.qualified_name or ctx.command.name}`")

        elif isinstance(error, commands.MissingPermissions):
            await ctx.error(description="You're not allowed to use this command.")

        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.error(description="I don't have enough permissions to execute this command.")

        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.error(description="This command is not usable in DM's.")

        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.error(description=f"You're on cooldown! Retry in `{error.retry_after:,.2f}` seconds.")

        elif isinstance(error, commands.CommandNotFound):
            await ctx.message.add_reaction("❓")
            await asyncio.sleep(15)
            await ctx.message.remove_reaction(emoji="❓", member=ctx.guild.me)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        check = await self.bot.db.fetchrow("SELECT EXISTS(SELECT 1 FROM guild_blacklist WHERE id=$1)", guild.id)

        if check["exists"]:
            try:
                embed = discord.Embed(color=self.bot.colors.red,
                                      description=f"Your guild / server tried to add me, but the ID is blacklisted. "
                                                  f"If you wish to know the reason, join the "
                                                  f"[Support server]({self.bot.invite_url})")
                await guild.owner.send(embed=embed)
                await guild.leave()
            except Exception:
                pass


def setup(bot):
    bot.add_cog(Listeners(bot))
