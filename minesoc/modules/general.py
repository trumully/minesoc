import discord
import time
import asyncio
import psutil
import platform

from discord.ext import commands


initial_time = time.time()


def measure_time(start, end):
    duration = int(end - start)
    return seconds_to_hms(duration)


def seconds_to_hms(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return "%d:%02d:%02d" % (hour, minutes, seconds)


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def number_of_channels(self, channels):
        return sum(1 for channel in channels if not isinstance(channel, discord.CategoryChannel))

    def number_of_bots(self, members):
        return sum(1 for member in members if member.bot)

    @commands.command()
    async def ping(self, ctx: commands.Context):
        """Pong!"""
        start_time = time.perf_counter()
        message = await ctx.send(
            embed=discord.Embed(color=discord.Color.greyple(), description=f"{self.bot.emojis.typing} Pinging ..."))
        ack = (time.perf_counter() - start_time) * 1000
        heartbeat = self.bot.latency * 1000

        async with ctx.typing():
            embed = discord.Embed(color=self.bot.colors.neutral)
            embed.add_field(name="💓 Heartbeat:", value=f"`{heartbeat:,.2f}ms`")
            embed.add_field(name="🗄 ACK:", value=f"`{ack:,.2f}ms`")
            await asyncio.sleep(2.5)
            await message.delete()
            await ctx.send(embed=embed)

    @commands.command()
    async def about(self, ctx: commands.Context):
        """General information about the bot"""
        app_info = await self.bot.application_info()
        guild_amount = len(self.bot.guilds)
        user_amount = len(self.bot.users)
        now_time = time.time()
        uptime = measure_time(initial_time, now_time)
        embed = discord.Embed(title=f"{self.bot.emojis.bot} About: {self.bot.user.name} | ID: {self.bot.user.id}",
                              description=f"{self.bot.description}\n"
                                          f"Serving **{user_amount} users** on **{guild_amount} guilds**",
                              color=self.bot.colors.neutral)
        embed.set_thumbnail(url=self.bot.user.avatar_url_as(static_format="png"))
        embed.add_field(name="Information", value=f"Owner: {self.bot.owner.mention}\nUptime: {uptime}")
        embed.add_field(name="Versions", value=f"{self.bot.emojis.python} {platform.python_version()}\n"
                                               f"{self.bot.emojis.discord} {discord.__version__}")
        embed.add_field(name="Process", value=f"{self.bot.emojis.cpu} {psutil.cpu_percent()}% / "
                                              f"{round(psutil.cpu_freq().current, 2)}MHz\n"
                                              f"{self.bot.emojis.vram} {psutil.virtual_memory()[2]}%")
        embed.add_field(name="Links", value=f"[Support Server]({self.bot.invite_url}) | [Invite]({self.bot.oauth()})",
                        inline=False)

        await ctx.send(embed=embed)

    @commands.command(aliases=["server"])
    @commands.guild_only()
    async def guild(self, ctx: commands.Context):
        """Guild information"""
        def_r = ctx.guild.default_role
        num_online = sum(member.status == discord.Status.online and not member.bot for member in ctx.guild.members)
        num_offline = sum(member.status == discord.Status.offline and not member.bot for member in ctx.guild.members)
        num_dnd = sum(member.status == discord.Status.dnd and not member.bot for member in ctx.guild.members)
        num_idle = sum(member.status == discord.Status.idle and not member.bot for member in ctx.guild.members)

        embed = discord.Embed(color=self.bot.colors.neutral, title=f"{ctx.guild.name}")
        embed.set_thumbnail(url=ctx.guild.icon_url_as(static_format="png", size=1024))
        embed.add_field(name="General", value=f"**ID:** {ctx.guild.id}\n"
                                              f"**Created:** {self.bot.format_datetime(ctx.guild.created_at)}\n"
                                              f"**Owner:** {ctx.guild.owner.mention}\n",
                        inline=False)
        embed.add_field(name=f"Roles `{len(ctx.guild.roles)}`",
                        value=f"{' | '.join([r.mention for r in ctx.guild.roles if r != def_r])}",
                        inline=False)
        number_of_bots = self.number_of_bots(ctx.guild.members)
        embed.add_field(name=f"Members `{len(ctx.guild.members)}`",
                        value=f"{self.bot.emojis.status_online} **{num_online}** online\n"
                              f"{self.bot.emojis.status_dnd} **{num_dnd}** dnd\n"
                              f"{self.bot.emojis.status_idle} **{num_idle}** idle\n"
                              f"{self.bot.emojis.status_offline} **{num_offline}** online\n"
                              f"{self.bot.emojis.bot} **{number_of_bots}** bots",
                        inline=True)
        embed.add_field(name=f"Channels ({self.number_of_channels(ctx.guild.channels)})",
                        value=f"{self.bot.emojis.text} {len(ctx.guild.text_channels)}\n"
                              f"{self.bot.emojis.voice} {len(ctx.guild.voice_channels)}",
                        inline=True)
        if ctx.guild.features:
            embed.add_field(name="__Features__",
                            value="\n".join([f.replace("_", " ").title() for f in ctx.guild.features]),
                            inline=False)

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(General(bot))
