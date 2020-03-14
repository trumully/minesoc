import re
import aiohttp
import html
import discord
import random

from bs4 import BeautifulSoup


class API:
    def __init__(self, bot):
        self.session = aiohttp.ClientSession()
        self.animal = Animal(self.session)
        self.trivia = Trivia(self.session)
        self.corona = Corona(self.session)
        self.bot = bot


class Trivia:
    class TriviaResponse:
        def __init__(self, response):
            self._info = response

            # 0 = Success
            # 1 = No Results
            # 2 = Invalid parameter
            self.response_code = response["response_code"]

            self.result = self._info["results"][0]

            self.question = html.unescape(self.result["question"])
            self.category = self.result["category"]
            self.type = self.result["type"]
            self.difficulty = self.result["difficulty"]

            self.correct = html.unescape(self.result["correct_answer"])
            self.answers = [html.unescape(a) for a in self.result["incorrect_answers"]]
            self.answers.append(self.correct)
            random.shuffle(self.answers)

            self.embed = self.__generate_embed__()

        def __generate_embed__(self):
            if self.response_code != 0:
                return self.response_code

            embed = discord.Embed(color=discord.Color(0xffffff))
            embed.title = "❔ Here's a question!"
            embed.description = f"{'An' if self.difficulty == 'easy' else 'A'} {self.difficulty} one from the " \
                                f"{self.category} category"
            embed.add_field(name="Question", value=self.question, inline=False)

            choices = "\n".join(f"[{index + 1}] {answer}" for index, answer in enumerate(self.answers))
            embed.add_field(name="Choices", value=f"```py\n{choices}```", inline=False)
            embed.set_footer(text="Input the number of your chosen answer")

            return embed

    def __init__(self, session: aiohttp.ClientSession()):
        self.session = session
        self.query_url = "https://opentdb.com/api.php?amount=1"

    async def get_trivia(self):
        async with self.session.get(self.query_url) as r:
            if r.status == 200:
                return self.TriviaResponse(response=await r.json())
            else:
                return False


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
            if r.status == 200:
                return self.DogResponse(response=await r.json())
            else:
                embed = discord.Embed(color=discord.Color.red(), title="Error!", description=await r.json()["message"])
                return self.DogResponse(response=None, error=embed)

    async def fetch_cat(self):
        async with self.session.get(self.cat_url) as r:
            if r.status == 200:
                return self.CatResponse(response=await r.json())
            else:
                embed = discord.Embed(color=discord.Color.red(), title="An error has occurred! Try again later.")
                return self.CatResponse(response=None, error=embed)


class Corona:
    class CoronaResponse:
        def __init__(self, response: BeautifulSoup):
            if response:
                self.stats = {}
                for div in response.find_all("div", {"id": "maincounter-wrap"}):
                    title = div.find("h1").text
                    stat = div.find("div", {"class": "maincounter-number"}).find("span").text
                    self.stats[title] = stat

                self.embed = self.__generate_embed()

        def __generate_embed(self):
            embed = discord.Embed()
            for key, value in self.stats.items():
                embed.add_field(name=key, value=value, inline=True)
            return embed

    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.url = "https://www.worldometers.info/coronavirus/"

    async def get_response(self):
        async with self.session.get(self.url) as response:
            if response.status == 200:
                return self.CoronaResponse(BeautifulSoup(await response.text()))
