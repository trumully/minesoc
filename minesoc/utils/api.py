import discord
import json
import aiohttp
import asyncio
import deviantart

from discord.ext import commands
from libneko.aggregates import Proxy
from dotenv import dotenv_values
from random import choice
from pathlib import Path

env_path = Path(__file__).parent.parent / ".env"
env_values = Proxy(dotenv_values(env_path))


class API:
    def __init__(self, bot):
        self.session = aiohttp.ClientSession()
        self.deviantart = DeviantArt(self.session)


class DeviantArt:

    class DeviantArtResponse:
        def __init__(self, response):
            self._info = choice(response["results"])
            self.mature = self._info["is_mature"]
            self.deviation_id = self._info["deviationid"]
            self.name = self._info["title"]
            self.author = self._info["author"]["username"]
            self.image = self._info["content"]["src"]
            self.url = self._info["url"]
            self.stats = self._info["stats"]
            self.category = self._info["category"]
            self.resolution = f"{self._info['content']['width']} x {self._info['content']['height']}"

            self.embed = self.__generate_embed()

        def __generate_embed(self):
            embed = discord.Embed(color=discord.Color.blue(), title=self.name, description=f"by {self.author}")
            embed.set_image(url=self.image)
            embed.set_footer(text=self.url)
            embed.add_field(name="Category", value=self.category)
            embed.add_field(name="Stats", value=f"Comments: {self.stats['comments']}\n"
                                                f"Favorites: {self.stats['favourites']}")

            return embed

    def __init__(self, session: aiohttp.ClientSession()):
        self.session = session
        self.da = deviantart.Api(env_values.DEVIANTART_CLIENT_ID, env_values.DEVIANTART_CLIENT_SECRET)
        self.access_token = self.da.access_token
        self.base_url ="https://www.deviantart.com/api/v1/oauth2/"

    async def browse_tags(self, tags: str):
        tags = tags.lower()
        async with self.session.get(
                self.base_url + f"browse/tags?tag={tags}&limit=50&access_token={self.access_token}") as r:
            return self.DeviantArtResponse(response=await r.json())

    async def browse_popular(self, query, category):
        url = self.base_url + "browse/popular?"
        if category is not None:
            category = category.lower()
            url += f"category_path={category}&"
        if query is not None:
            query = query.lower()
            url += f"q={query}&"
        url += f"timerange=1week&limit=50&access_token={self.access_token}"
        async with self.session.get(url) as r:
            return self.DeviantArtResponse(response=await r.json())

