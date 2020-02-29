# music.py
# Uses an alternative library for playing music

import math
import re

import discord
import lavalink
import spotipy
from discord.ext import commands

url_rx = re.compile("https?://(?:www\\.)?.+")  # noqa: W605
spotify_url_rx = re.compile("https?://(?:open\\.)?.+")


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.spotify_types = ["album", "playlist", "track"]

        if not hasattr(bot, "lavalink"):  # This ensures the client isn"t overwritten during cog reloads.
            bot.lavalink = lavalink.Client(bot.user.id, loop=self.bot.loop)
            bot.lavalink.add_node(**self.bot.config.lavalink)
            bot.add_listener(bot.lavalink.voice_update_handler, "on_socket_response")

        bot.lavalink.add_event_hook(self.track_hook)

    async def queue_spotify(self, tracks, player: lavalink.DefaultPlayer, requester):
        for i in range(len(tracks)):
            track = tracks[i]["track"]

            song = track["name"]
            artist = track["artists"][0]["name"]

            if not track["is_local"]:
                search = f"ytsearch:{song} {artist} lyrics"
                result = await player.node.get_tracks(search)
                if result["tracks"]:
                    if not player.is_playing and i == 0:
                        await player.play(lavalink.AudioTrack.build(track=result["tracks"][0], requester=requester))
                    else:
                        player.add(track=result["tracks"][0], requester=requester)

    def cog_unload(self):
        self.bot.lavalink._event_hooks.clear()

    async def cog_before_invoke(self, ctx):
        guild_check = ctx.guild is not None
        #  This is essentially the same as `@commands.guild_only()`
        #  except it saves us repeating ourselves (and also a few lines).

        if guild_check:
            await self.ensure_voice(ctx)
            #  Ensure that the bot and command author share a mutual voicechannel.

        return guild_check

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(error)
            # The above handles errors thrown in this cog and shows them to the user.
            # This shouldn't be a problem as the only errors thrown in this cog are from `ensure_voice`
            # which contain a reason string, such as "Join a voice channel" etc. You can modify the above
            # if you want to do things differently.

    async def track_hook(self, event):
        if isinstance(event, lavalink.events.QueueEndEvent):
            guild_id = int(event.player.guild_id)
            await self.connect_to(guild_id, None)
            # Disconnect from the channel -- there's nothing else to play.
        if isinstance(event, lavalink.events.TrackStartEvent):
            context = event.player.fetch("context")
            track = event.player.fetch("track")
            embed = discord.Embed(color=discord.Color.blurple(), title="Now Playing",
                                  description=f"[{event.track.title}]({track})")
            await context.send(embed=embed)

    async def connect_to(self, guild_id: int, channel_id: str):
        """ Connects to the given voice channel ID. A channel_id of `None` means disconnect. """
        ws = self.bot._connection._get_websocket(guild_id)
        await ws.voice_state(str(guild_id), channel_id)
        # The above looks dirty, we could alternatively use `bot.shards[shard_id].ws` but that assumes
        # the bot instance is an AutoShardedBot.

    @commands.command(aliases=["p"])
    async def play(self, ctx, *, query: str):
        """ Searches and plays a song from a given query. """
        player = self.bot.lavalink.players.get(ctx.guild.id)
        player.store("context", ctx)

        query = query.strip("<>")

        async with ctx.typing():
            embed = discord.Embed(color=discord.Color.blurple())

            if "open.spotify.com" in query or query.count(":") >= 2:
                spotify_type = None
                for i in self.spotify_types:
                    if i in query:
                        spotify_type = i

                credentials = spotipy.SpotifyClientCredentials(client_id=self.bot.config.spotify_id,
                                                               client_secret=self.bot.config.spotify_secret)
                token = credentials.get_access_token()
                sp = spotipy.Spotify(auth=token)

                if re.match(spotify_url_rx, query):
                    spotify_id = re.search(f"{spotify_type}/(.*)\\?si=", query).group(
                        1) if "?si=" in query else re.search(f"{spotify_type}/(.*)", query).group(1)
                else:
                    spotify_id = query.split(":")[-1]

                if spotify_type == "track":
                    results = sp.track(spotify_id)
                    track = results
                    search = f"ytsearch:{track['name']} {track['artists'][0]['name']}"
                    res = await player.node.get_tracks(search)

                    if res["tracks"]:
                        to_play = res["tracks"][0]
                        player.add(requester=ctx.author.id, track=to_play)

                    embed.title = "Track Enqueued!"
                    embed.description = f"[{to_play['info']['title']}]({to_play['info']['uri']})"

                else:
                    if spotify_type == "album":
                        results = sp.album_tracks(spotify_id)
                    else:
                        results = sp.playlist_tracks(spotify_id)

                    tracks = results["items"]
                    while results["next"]:
                        results = sp.next(results)
                        tracks.extend(results["items"])

                    self.task = self.bot.loop.create_task(self.queue_spotify(tracks, player, ctx.author.id))

            else:
                if not re.match(url_rx, query) or not query.startswith("ytsearch:"):
                    query = f"ytsearch:{query}"

                results = await player.node.get_tracks(query)

                if not results or not results["tracks"]:
                    return await ctx.send("Nothing found!")

                if results["loadType"] == "PLAYLIST_LOADED":
                    tracks = results["tracks"]

                    for track in tracks:
                        player.add(requester=ctx.author.id, track=track)

                    embed.title = "Playlist Enqueued!"
                    embed.description = f"{results['playlistInfo']['name']} - {len(tracks)} tracks"
                else:
                    track = results["tracks"][0]
                    embed.title = "Track Enqueued"
                    embed.description = f"[{track['info']['title']}]({track['info']['uri']})"
                    player.add(requester=ctx.author.id, track=track)

            player.store("track", track["info"]["uri"])

        await ctx.send(embed=embed)

        if not player.is_playing:
            await player.play()

    @commands.command()
    async def seek(self, ctx, *, seconds: int):
        """ Seeks to a given position in a track. """
        player = self.bot.lavalink.players.get(ctx.guild.id)

        track_time = player.position + (seconds * 1000)
        await player.seek(track_time)

        await ctx.send(f"Moved track to **{lavalink.utils.format_time(track_time)}**")

    @commands.command(aliases=["forceskip"])
    async def skip(self, ctx):
        """ Skips the current track. """
        player = self.bot.lavalink.players.get(ctx.guild.id)

        if not player.is_playing:
            return await ctx.send("Not playing.")

        await player.skip()
        await ctx.send("⏭ | Skipped.")

    @commands.command()
    async def stop(self, ctx):
        """ Stops the player and clears its queue. """
        player = self.bot.lavalink.players.get(ctx.guild.id)

        if not player.is_playing:
            return await ctx.send("Not playing.")

        player.queue.clear()
        await player.stop()
        try:
            self.task.cancel()
        except Exception:
            pass
        await ctx.send("⏹ | Stopped.")

    @commands.command(aliases=["np", "n", "playing"])
    async def now(self, ctx):
        """ Shows some stats about the currently playing song. """
        player = self.bot.lavalink.players.get(ctx.guild.id)

        if not player.current:
            return await ctx.send("Nothing playing.")

        position = lavalink.utils.format_time(player.position)
        if player.current.stream:
            duration = "🔴 LIVE"
        else:
            duration = lavalink.utils.format_time(player.current.duration)
        song = f"**[{player.current.title}]({player.current.uri})**\n({position}/{duration})"

        embed = discord.Embed(color=discord.Color.blurple(),
                              title="Now Playing", description=song)
        await ctx.send(embed=embed)

    @commands.command()
    async def queue(self, ctx, page: int = 1):
        """ Shows the player"s queue. """
        player = self.bot.lavalink.players.get(ctx.guild.id)

        if not player.queue:
            return await ctx.send("Nothing queued.")

        items_per_page = 10
        pages = math.ceil(len(player.queue) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue_list = ""
        for index, track in enumerate(player.queue[start:end], start=start):
            queue_list += f"`{index + 1}.` [**{track.title}**]({track.uri})\n"

        embed = discord.Embed(colour=discord.Color.blurple(),
                              description=f"**{len(player.queue)} tracks**\n\n{queue_list}")
        embed.set_footer(text=f"Viewing page {page}/{pages}")
        await ctx.send(embed=embed)

    @commands.command(aliases=["resume"])
    async def pause(self, ctx):
        """ Pauses/Resumes the current track. """
        player = self.bot.lavalink.players.get(ctx.guild.id)

        if not player.is_playing:
            return await ctx.send("Not playing.")

        if player.paused:
            await player.set_pause(False)
            await ctx.send("⏯ | Resumed")
        else:
            await player.set_pause(True)
            await ctx.send("⏯ | Paused")

    @commands.command(aliases=["vol"])
    async def volume(self, ctx, volume: int = None):
        """ Changes the player"s volume (0-1000). """
        player = self.bot.lavalink.players.get(ctx.guild.id)

        if not volume:
            return await ctx.send(f"🔈 | {player.volume}%")

        await player.set_volume(volume)  # Lavalink will automatically cap values between, or equal to 0-1000.
        await ctx.send(f"🔈 | Set to {player.volume}%")

    @commands.command()
    async def shuffle(self, ctx):
        """ Shuffles the player"s queue. """
        player = self.bot.lavalink.players.get(ctx.guild.id)
        if not player.is_playing:
            return await ctx.send("Nothing playing.")

        player.shuffle = not player.shuffle
        await ctx.send("🔀 | Shuffle " + ("enabled" if player.shuffle else "disabled"))

    @commands.command(aliases=["loop"])
    async def repeat(self, ctx):
        """ Repeats the current song until the command is invoked again. """
        player = self.bot.lavalink.players.get(ctx.guild.id)

        if not player.is_playing:
            return await ctx.send("Nothing playing.")

        player.repeat = not player.repeat
        await ctx.send("🔁 | Repeat " + ("enabled" if player.repeat else "disabled"))

    @commands.command()
    async def remove(self, ctx, index: int):
        """ Removes an item from the player"s queue with the given index. """
        player = self.bot.lavalink.players.get(ctx.guild.id)

        if not player.queue:
            return await ctx.send("Nothing queued.")

        if index > len(player.queue) or index < 1:
            return await ctx.send(f"Index has to be **between** 1 and {len(player.queue)}")

        removed = player.queue.pop(index - 1)  # Account for 0-index.

        await ctx.send(f"Removed **{removed.title}** from the queue.")

    @commands.command()
    async def find(self, ctx, *, query):
        """ Lists the first 10 search results from a given query. """
        player = self.bot.lavalink.players.get(ctx.guild.id)

        if not query.startswith("ytsearch:") and not query.startswith("scsearch:"):
            query = "ytsearch:" + query

        results = await player.node.get_tracks(query)

        if not results or not results["tracks"]:
            return await ctx.send("Nothing found.")

        tracks = results["tracks"][:10]  # First 10 results

        o = ""
        for index, track in enumerate(tracks, start=1):
            track_title = track["info"]["title"]
            track_uri = track["info"]["uri"]
            o += f"`{index}.` [{track_title}]({track_uri})\n"

        embed = discord.Embed(color=discord.Color.blurple(), description=o)
        await ctx.send(embed=embed)

    @commands.command(aliases=["dc", "l", "leave"])
    async def disconnect(self, ctx):
        """ Disconnects the player from the voice channel and clears its queue. """
        player = self.bot.lavalink.players.get(ctx.guild.id)

        if not player.is_connected:
            return await ctx.send("Not connected.")

        if not ctx.author.voice or (player.is_connected and ctx.author.voice.channel.id != int(player.channel_id)):
            return await ctx.send("You're not in my voicechannel!")

        player.queue.clear()
        await player.stop()
        try:
            self.task.cancel()
        except Exception:
            pass
        await self.connect_to(ctx.guild.id, None)
        await ctx.send("*⃣ | Disconnected.")

    @commands.command()
    async def summon(self, ctx):
        await self.connect_to(ctx.guild.id, str(ctx.author.voice.channel.id))

    async def ensure_voice(self, ctx):
        """ This check ensures that the bot and command author are in the same voicechannel. """
        player = self.bot.lavalink.players.create(ctx.guild.id, endpoint=str(ctx.guild.region))
        # Create returns a player if one exists, otherwise creates.

        should_connect = ctx.command.name in ("play", "summon",)  # Add commands that require joining voice to work.

        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandInvokeError("Join a voice channel first.")

        if not player.is_connected:
            if not should_connect:
                raise commands.CommandInvokeError("Not connected.")

            permissions = ctx.author.voice.channel.permissions_for(ctx.me)

            if not permissions.connect or not permissions.speak:  # Check user limit too?
                raise commands.CommandInvokeError("I need the `CONNECT` and `SPEAK` permissions.")

            player.store("channel", ctx.channel.id)
            await self.connect_to(ctx.guild.id, str(ctx.author.voice.channel.id))
        else:
            if int(player.channel_id) != ctx.author.voice.channel.id and ctx.command.name != "summon":
                raise commands.CommandInvokeError("You need to be in my voice channel.")


def setup(bot):
    bot.add_cog(Music(bot))
