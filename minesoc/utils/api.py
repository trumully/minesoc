import discord
import json
import aiohttp
import asyncio
import deviantart
import re

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
        self.animal = Animal(self.session)
        self.bot = bot


class DeviantArt:

    class DeviantArtResponse:
        def __init__(self, response, error: discord.Embed = None):
            if error is None:
                self._info = choice(response["results"])
                self.mature = self._info["is_mature"]
                self.deviation_id = self._info["deviationid"]

                self.name = self._info["title"]
                self.author = self._info["author"]
                self.username = self.author["username"]
                self.user_icon = self.author["usericon"]

                self.content = self._info["content"]
                self.image = self.content["src"]
                self.resolution = f"{self.content['width']} x {self.content['height']}"

                self.url = self._info["url"]
                self.stats = self._info["stats"]
                self.category = self._info["category"]

                self.embed = self.__generate_embed()

            else:
                self.embed = error

        def __generate_embed(self):
            embed = discord.Embed(color=discord.Color.blue(), title=self.name, url=self.url)
            embed.set_author(name=self.username, icon_url=self.user_icon)
            embed.set_image(url=self.image)
            embed.add_field(name="Category:", value=self.category)
            embed.add_field(name="Stats:", value=f"💬 {self.stats['comments']} | ⭐ {self.stats['favourites']}")
            embed.add_field(name="Resolution:", value=self.resolution)

            return embed

    def __init__(self, session: aiohttp.ClientSession()):
        self.session = session
        self.da = deviantart.Api(env_values.DEVIANTART_CLIENT_ID, env_values.DEVIANTART_CLIENT_SECRET)
        self.access_token = self.da.access_token
        self.base_url = "https://www.deviantart.com/api/v1/oauth2/"

    async def browse_tags(self, tags: str):
        tags = tags.lower()
        url = self.base_url + f"browse/tags?tag={tags}&limit=50&access_token={self.access_token}"
        async with self.session.get(url) as r:
            if r.status == 200:
                return self.DeviantArtResponse(response=await r.json())
            else:
                response = await r.json()
                error = f"{response['error']}: {response['error_description']}"
                if response["error"] == "invalid_token":
                    self.da = deviantart.Api(env_values.DEVIANTART_CLIENT_ID, env_values.DEVIANTART_CLIENT_SECRET)
                    self.access_token = self.da.access_token
                embed = discord.Embed(color=discord.Color.red(), title="An error has occurred!",
                                      description=f"Error {r.status}\n`{error}`")

                return self.DeviantArtResponse(response=None, error=embed)

    async def browse_popular(self, query: str = None, category: str = None):
        url = self.base_url + "browse/popular?"
        if category:
            category = category.lower()
            url += f"category_path={category}&"
        if query:
            query = query.lower()
            url += f"q={query}&"
        url += f"timerange=1week&limit=50&access_token={self.access_token}"
        async with self.session.get(url) as r:
            if r.status == 200:
                return self.DeviantArtResponse(response=await r.json())
            else:
                response = await r.json()
                error = f"{response['error']}: {response['error_description']}"
                if response["error"] == "invalid_token":
                    self.da = deviantart.Api(env_values.DEVIANTART_CLIENT_ID, env_values.DEVIANTART_CLIENT_SECRET)
                    self.access_token = self.da.access_token
                embed = discord.Embed(color=discord.Color.red(), title="An error has occurred!",
                                      description=f"Error {r.status}\n`{error}`")

                return self.DeviantArtResponse(response=None, error=embed)


class Animal:

    class DogResponse:
        def __init__(self, response, error: discord.Embed = None):
            if error is None:
                self._info = response
                self.status = self._info["status"]
                self.url = self._info["message"]
                breed_search = re.search("breeds/(.*)/", self.url)
                self.breed = breed_search.group(1).replace("-", " ").title()

                self.embed = self.__generate_embed()

            else:
                self.embed = error

        def __generate_embed(self):
            embed = discord.Embed(color=discord.Color.blue())
            embed.title = self.breed
            embed.set_image(url=self.url)
            return embed

    class CatResponse:
        def __init__(self, response, error: discord.Embed = None):
            if error is None:
                self.image = response["file"]
                self.embed = self.__generate_embed()
            else:
                self.embed = error

        def __generate_embed(self):
            embed = discord.Embed(color=discord.Color.blue())
            embed.set_image(url=self.image)

            return embed

    def __init__(self, session: aiohttp.ClientSession()):
        self.session = session
        self.dog_url = "https://dog.ceo/api/breed"
        self.cat_url = "https://aws.random.cat/meow"

    async def fetch_dog(self, breed: str = None, sub_breed: str = None):
        if breed and sub_breed:
            url = self.dog_url + f"/{breed.lower()}/{sub_breed.lower()}/images/random"
        elif breed:
            url = self.dog_url + f"/{breed.lower()}/images/random"
        else:
            url = self.dog_url + "s/image/random"
        async with self.session.get(url) as r:
            response = await r.json()
            if response["status"] == "success":
                return self.DogResponse(response=response)
            else:
                embed = discord.Embed(color=discord.Color.red(), title="Error!", description=response["message"])
                return self.DogResponse(response=None, error=embed)

    async def fetch_cat(self):
        async with self.session.get(self.cat_url) as r:
            if r.status == 200:
                return self.CatResponse(response=await r.json())
            else:
                embed = discord.Embed(color=discord.Color.red(), title="An error has occurred! Try again later.")
                return self.CatResponse(response=None, error=embed)
