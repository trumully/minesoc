from datetime import timedelta, datetime

import discord
from discord.ext import commands
from libneko import pag

from minesoc.utils import errors


class Internal(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.webhook_log_channel = None

    async def cog_check(self, ctx):
        if not await self.bot.is_owner(ctx.author):
            raise commands.NotOwner
        elif ctx.guild.id != self.bot.dev_guild.id:
            raise errors.OnlyDevGuild
        else:
            return True

    async def update_emoji_list(self):
        guild = self.bot.dev_guild
        channel = discord.utils.get(guild.text_channels, name="emoji-list")
        if guild and channel:
            animated_emojis = list()
            normal_emojis = list()

            try:
                await channel.purge()

                for emoji in guild.emojis:
                    if emoji.animated:
                        animated_emojis.append(f"{emoji} - `{emoji}`\n")
                    else:
                        normal_emojis.append(f"{emoji} - `{emoji}`\n")
                else:
                    animated_emojis = " ".join(sorted(animated_emojis))
                    normal_emojis = " ".join(sorted(normal_emojis))
                    self.bot.logger.info("Emoji list is updating.")
                    await channel.send(animated_emojis + "\n")
                    await channel.send(normal_emojis)
            except Exception as ex:
                self.bot.logger.error(ex, exc_info=ex)
        else:
            self.bot.logger.warning("Emojis channel can't be found.")

    async def purge_logs(self):
        purged = await self._webhook_log_channel.purge(
            before=datetime.utcfromtimestamp(self.bot.start_time) - timedelta(days=0))
        if purged:
            await self._webhook_log_channel.edit(
                topic=f"{self.bot.custom_emojis.notification} Last purge: {self.bot.format_datetime(datetime.now())}")
            return purged
        else:
            return False

    @commands.Cog.listener()
    async def on_ready(self):
        self._webhook_log_channel = self.bot.get_channel(self.bot.config.webhook_id)
        await self.purge_logs()
        await self.update_emoji_list()

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild: discord.Guild, before, after):
        if guild.id == self.bot.dev_guild.id:
            if len(before) < len(after):
                emoji = [emoji for emoji in after if emoji not in before][0]
                self.bot.custom_emojis.set_emoji(emoji)
            elif len(before) > len(after):
                emoji = [emoji for emoji in before if emoji not in after][0]
                self.bot.custom_emojis.remove_emoji(emoji)
            else:
                self.bot.custom_emojis.reinit()

    @commands.command()
    async def update_emojis(self, ctx: commands.Context):
        await self.update_emoji_list()
        await ctx.success(description="Updated internal emoji list.")

    @commands.group(invoke_without_command=True)
    async def logs(self, ctx: commands.Context):
        """Internal log management"""
        await ctx.send_help(ctx.command)

    @logs.command(name="purge")
    async def logs_purge(self, ctx: commands.Context):
        """Purge all messages before bot start"""
        purged = await self.purge_logs()
        if purged:
            await ctx.success(
                description=f"Purging messages older than (`{self.bot.start_time.strftime('%X %x')}`) "
                            f"(`{len(purged)} messages`).")
        else:
            await ctx.info(description="No messages have been purged.")

    @logs.command(name="send")
    async def logs_send(self, ctx: commands.Context, log):
        try:
            with open(f"logs/{log}.log", "r") as fp:
                pag.StringNavigatorFactory(max_lines=15, prefix="```", suffix="```").add_lines(fp.read()).start(ctx)
        except FileNotFoundError:
            await ctx.error(description="Logging file doesn't exist.")

    @logs_purge.before_invoke
    async def before_logs_purge(self, ctx: commands.Context):
        if not self.webhook_log_channel:
            await self.bot.wait_until_ready()
            self.webhook_log_channel = self.bot.dev_guild.get_channel(self.bot.config.webhook_id)

            if not self.webhook_log_channel:
                raise commands.DisabledCommand


def setup(bot):
    bot.add_cog(Internal(bot))
