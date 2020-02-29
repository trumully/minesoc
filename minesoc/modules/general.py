import datetime
import platform
import re
import textwrap
import time
from io import BytesIO

import aiohttp
import discord
import psutil
import spotipy
from PIL import Image, ImageDraw, ImageFont
from discord.ext import commands


def measure_time(start, end):
    duration = int(end - start)
    return seconds_to_hms(duration)


def seconds_to_hms(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    if hour == 0:
        return "%02d:%02d" % (minutes, seconds)
    return "%d:%02d:%02d" % (hour, minutes, seconds)


class SpotifyImage:
    def __init__(self):
        self.font = ImageFont.truetype("arial-unicode-ms.ttf", 16)
        self.session = aiohttp.ClientSession()

    def draw(self, name, artists, color, album_bytes: BytesIO, track_duration=None, time_end=None):
        album_bytes = Image.open(album_bytes)
        size = (160, 160)
        album_bytes = album_bytes.resize(size)

        w, h = (500, 170)
        im = Image.new("RGBA", (w, h), color)

        im_draw = ImageDraw.Draw(im)
        off_x, off_y, w, h = (5, 5, 495, 165)

        font_size = 1
        max_size = 20
        img_fraction = 0.75

        medium_font = ImageFont.truetype("arial-unicode-ms.ttf", font_size)
        while medium_font.getsize(name)[0] < img_fraction * im.size[0]:
            font_size += 1
            medium_font = ImageFont.truetype("arial-unicode-ms.ttf", font_size)

        if font_size >= max_size:
            font_size = max_size

        font_size -= 1
        medium_font = ImageFont.truetype("arial-unicode-ms.ttf", font_size)

        im_draw.rectangle((off_x, off_y, w, h), fill=(5, 5, 25))
        im_draw.text((175, 15), name, font=medium_font, fill=(255, 255, 255, 255))

        artist_text = ", ".join(artists)
        artist_text = "\n".join(textwrap.wrap(artist_text, width=35))
        im_draw.text((175, 45), artist_text, font=self.font, fill=(255, 255, 255, 255))

        if time_end is not None and track_duration is not None:
            now = datetime.datetime.utcnow()
            percentage_played = 1 - (time_end - now).total_seconds() / track_duration.total_seconds()
            im_draw.rectangle((175, 130, 375, 125), fill=(64, 64, 64, 255))
            im_draw.rectangle((175, 130, 175 + int(200 * percentage_played), 125), fill=(254, 254, 254, 255))

            track_duration = track_duration.total_seconds()
            duration = f"{seconds_to_hms(track_duration * percentage_played)} / {seconds_to_hms(track_duration)}"
            im_draw.text((175, 130), duration, font=self.font, fill=(255, 255, 255, 255))
        else:
            im_draw.text((175, 130), seconds_to_hms(track_duration), font=self.font, fill=(255, 255, 255, 255))

        im.paste(album_bytes, (5, 5))

        spotify_logo = Image.open("images/spotify-512.png")
        spotify_logo = spotify_logo.resize((48, 48))
        im.paste(spotify_logo, (437, 15), spotify_logo)

        buffer = BytesIO()
        im.save(buffer, "png")
        buffer.seek(0)

        return buffer

    async def fetch_cover(self, cover_url):
        async with self.session as s:
            async with s.get(cover_url) as r:
                if r.status == 200:
                    return await r.read()


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def number_of_channels(self, channels):
        return sum(1 for channel in channels if not isinstance(channel, discord.CategoryChannel))

    def number_of_bots(self, members):
        return sum(1 for member in members if member.bot)

    def format_permission(self, permissions: discord.Permissions, separator=", "):
        output = list()
        for perm in permissions:
            if perm[1]:
                output.append(perm[0].replace("_", " ").title())
        else:
            return separator.join(output)

    @commands.command()
    async def ping(self, ctx: commands.Context):
        """Pong!"""
        start_time = time.perf_counter()
        ack = (time.perf_counter() - start_time) * 1000
        heartbeat = self.bot.latency * 1000

        async with ctx.typing():
            embed = discord.Embed(color=self.bot.colors.neutral)
            embed.add_field(name="💓 Heartbeat:", value=f"`{heartbeat:,.2f}ms`")
            embed.add_field(name="🗄 ACK:", value=f"`{ack:,.2f}ms`")

        await ctx.send(embed=embed)

    @commands.command(aliases=["minesoc"])
    async def about(self, ctx: commands.Context):
        """General information about the bot"""
        guild_amount = len(self.bot.guilds)
        user_amount = len(self.bot.users)
        links = [f"[Support Server]({self.bot.invite_url})", f"[Invite]({self.bot.oauth()})",
                 f"[Trello](https://trello.com/b/Lf0eO7wv)", f"[Github](https://github.com/trumully/minesoc)"]
        uptime = datetime.timedelta(microseconds=(time.time_ns() - self.bot.start_time) / 1000)
        uptime = str(uptime).split(".")[0]
        embed = discord.Embed(
            title=f"{self.bot.custom_emojis.minesoc} About: {self.bot.user.name} | ID: {self.bot.user.id}",
            description=f"{self.bot.description}\n"
                        f"Serving **{user_amount} users** on **{guild_amount} guilds**",
            color=self.bot.colors.neutral)
        embed.set_thumbnail(url=self.bot.user.avatar_url_as(static_format="png"))
        embed.add_field(name="Information", value=f"Owner: {self.bot.owner.mention}\nUptime: {uptime}")
        embed.add_field(name="Versions", value=f"{self.bot.custom_emojis.python} {platform.python_version()}\n"
                                               f"{self.bot.custom_emojis.discord} {discord.__version__}")
        embed.add_field(name="Process", value=f"{self.bot.custom_emojis.cpu} {psutil.cpu_percent()}% / "
                                              f"{round(psutil.cpu_freq().current, 2)}MHz\n"
                                              f"{self.bot.custom_emojis.vram} {psutil.virtual_memory()[2]}%")
        embed.add_field(name="Links", value=" | ".join(links), inline=False)

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
        statuses = {f"{self.bot.custom_emojis.status_online}": [num_online, "Online"],
                    f"{self.bot.custom_emojis.status_offline}": [num_offline, "Offline"],
                    f"{self.bot.custom_emojis.status_dnd}": [num_dnd, "DnD"],
                    f"{self.bot.custom_emojis.status_idle}": [num_idle, "Idle"]}

        status_list = [f"{key} **{value[0]}** {value[-1]}" for key, value in statuses.items() if value[0] >= 1]

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
                        value=f"{' | '.join(status_list)} | "
                              f"{self.bot.custom_emojis.bot} **{number_of_bots}** "
                              f"{'Bots' if number_of_bots > 1 else 'Bot'}",
                        inline=True)
        embed.add_field(name=f"Channels `{self.number_of_channels(ctx.guild.channels)}`",
                        value=f"{self.bot.custom_emojis.text} {len(ctx.guild.text_channels)} | "
                              f"{self.bot.custom_emojis.voice} {len(ctx.guild.voice_channels)}",
                        inline=False)
        if ctx.guild.features:
            embed.add_field(name="__Features__",
                            value="\n".join([f.replace("_", " ").title() for f in ctx.guild.features]),
                            inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    async def member(self, ctx, *, member: discord.Member = None):
        """Member information"""
        member = ctx.author if member is None else member
        embed = discord.Embed(color=member.color)

        embed.set_author(name=f"{member.name} ({member.id})")
        embed.set_thumbnail(url=member.avatar_url_as(static_format="png", size=1024))
        embed.add_field(name="Joined", value=self.bot.format_datetime(member.joined_at), inline=False)
        embed.add_field(name="Created", value=self.bot.format_datetime(member.created_at), inline=False)
        embed.add_field(name=f"Roles ({len(member.roles) - 1})",
                        value=" | ".join([r.mention for r in member.roles if r != ctx.guild.default_role]),
                        inline=False)
        if isinstance(member.activity, discord.Spotify):
            embed.add_field(name=f"Spotify",
                            value=f"Listening to **{member.activity.title}** from "
                                  f"**{', '.join(member.activity.artists)}**",
                            inline=False)
        else:
            embed.add_field(name=f"Activity",
                            value=f"{member.activity.type.name.title()}"
                                  f"{' to' if member.activity.type.name == 'listening' else ''} "
                                  f"{member.activity.name}",
                            inline=False)
        embed.add_field(name="Permissions", value=self.format_permission(member.permissions_in(ctx.channel)))

        await ctx.send(embed=embed)

    @commands.command()
    async def avatar(self, ctx: commands.Context, *, member: discord.Member = None):
        """Avatar from a member"""
        member = ctx.author if member is None else member
        embed = discord.Embed(color=member.color, title=str(member))
        embed.set_image(url=member.avatar_url_as(static_format="png", size=1024))

        await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.bot_has_permissions(attach_files=True)
    async def spotify(self, ctx, user: discord.Member = None):
        """Get a user's Spotify status as an image."""
        user = ctx.author if not user else user
        if user.bot:
            return

        async with ctx.typing():
            for activity in user.activities:
                if isinstance(activity, discord.Spotify):
                    card = SpotifyImage()

                    album_bytes = await card.fetch_cover(activity.album_cover_url)
                    color = activity.color.to_rgb()

                    end = activity.end
                    duration = activity.duration
                    buffer = card.draw(activity.title, activity.artists, color, BytesIO(album_bytes), duration, end)
                    url = f"<https://open.spotify.com/track/{activity.track_id}>"
                    await ctx.message.delete()
                    embed = discord.Embed(
                        description=f"{self.bot.custom_emojis.spotify} {user.mention} is listening to:\n**{url}**",
                        color=activity.color)
                    embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.avatar_url)
                    file = discord.File(fp=buffer, filename="spotify.png")
                    embed.set_image(url="attachment://spotify.png")
                    return await ctx.send(embed=embed, file=file)

            embed = discord.Embed(color=self.bot.colors.spotify)
            embed.description = f"{self.bot.custom_emojis.spotify} " \
                                f"{f'{user.mention} is' if user is not ctx.author else 'You are'} " \
                                f"currently not listening to Spotify."
            await ctx.send(embed=embed)

    @spotify.command(name="get")
    async def spotify_get(self, ctx, spotify_link):
        """Get a Spotify track as an image."""
        async with ctx.typing():
            credentials = spotipy.SpotifyClientCredentials(client_id=str(self.bot.config.spotify_id),
                                                           client_secret=str(self.bot.config.spotify_secret))
            token = credentials.get_access_token()
            spotify = spotipy.Spotify(auth=token)

            uri = "spotify:"
            res = re.search("com/(.*)\\?si=", spotify_link).group(1)
            res = res.replace("/", ":")
            uri += res
            track = uri.split(":")[2]

            card = SpotifyImage()
            result = spotify.track(track)
            url = f"<{result['external_urls']['spotify']}>"
            album_bytes = await card.fetch_cover(f"{result['album']['images'][0]['url']}")
            track_name = result["name"]
            track_artists = (i["name"] for i in result["artists"])
            duration = result["duration_ms"] / 1000
            buffer = card.draw(track_name, track_artists, self.bot.colors.spotify.to_rgb(),
                               BytesIO(album_bytes), duration)
            await ctx.message.delete()
            await ctx.send(f"{self.bot.custom_emojis.spotify} **{url}** {ctx.author.mention}",
                           file=discord.File(fp=buffer, filename="spotify.png"))

    @spotify.error
    async def spotify_error(self, ctx, error):
        if isinstance(error, spotipy.SpotifyException):
            await ctx.error(description=f"Could not provide given track or the Spotify authentication is invalid.\n"
                                        f"{error}")


def setup(bot):
    bot.add_cog(General(bot))
