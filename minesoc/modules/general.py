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
        embed = discord.Embed(color=self.bot.colors.neutral)

        embed.set_author(name=f"{ctx.guild.name} ({ctx.guild.id})")
        embed.set_thumbnail(url=ctx.guild.icon_url_as(static_format="png", size=1024))
        embed.add_field(name="Owner", value=ctx.guild.owner.mention, inline=False)
        embed.add_field(name="Region", value=ctx.guild.region)
        embed.add_field(name="Created", value=self.bot.format_datetime(ctx.guild.created_at), inline=False)
        embed.add_field(name=f"Channels ({self.number_of_channels(ctx.guild.channels)})",
                        value=f"#️⃣: `{len(ctx.guild.text_channels)}`\n"
                              f"🔈: `{len(ctx.guild.voice_channels)}`",
                        inline=False)
        embed.add_field(name=f"Roles ({len(ctx.guild.roles)})",
                        value=" | ".join([r.mention for r in ctx.guild.roles if r != ctx.guild.default_role]),
                        inline=False)
        if ctx.guild.features:
            embed.add_field(name="Features",
                            value="\n".join([f.replace("_", " ").title() for f in ctx.guild.features]),
                            inline=False)
        number_of_bots = self.number_of_bots(ctx.guild.members)
        embed.add_field(name="Other",
                        value=f"Members: `{len(ctx.guild.members) - number_of_bots}`\n"
                              f"Bots: `{number_of_bots}`\nEmojis: `{len(ctx.guild.emojis)}`",
                        inline=False)

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(General(bot))
