import re
import aiohttp
import html
import discord
import random
import json
import pandas as pd

from matplotlib import pyplot as plt
from io import StringIO, BytesIO
from datetime import datetime
from PIL import Image


class API:
    def __init__(self, bot):
        self.session = aiohttp.ClientSession()
        self.animal = Animal(self.session)
        self.trivia = Trivia(self.session)
        self.corona = Covid(self.session)
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


class Covid:
    class CovidResponse:
        def __init__(self, response, data_type):
            if response is not False:
                self._info = response
                self.data_type = data_type
                self.stats = self._info.get("latest", None)
                if self._info is None:
                    self.embed = discord.Embed(color=discord.Color.red(), title="An error occurred.")
                else:
                    self.embed = self.__generate_embed()
            else:
                self.embed = discord.Embed(color=discord.Color.red(), title="An error occurred.")

        def __generate_graph(self):
            embed = discord.Embed()
            flag = f":flag_{self._info['country_code'].lower()}:"
            title = f"COVID-19 data for {self._info['country'].title()}"
            embed.title = f"{flag} {title}"
            embed.add_field(name="Latest", value=self._info["latest"])

            data = {"date": [i for i in self._info["history"].keys()],
                    "values": [i for i in self._info["history"].values()]}
            self.df = pd.DataFrame(data, columns=["date", "values"])
            self.df["date"] = pd.to_datetime(self.df["date"])
            self.df.index = self.df["date"]
            del self.df["date"]
            self.df.resample("D").sum().plot()
            buffer = BytesIO()
            plt.suptitle(title, fontsize=16)
            plt.savefig(buffer, format="png")
            buffer.seek(0)
            self.file = discord.File(fp=buffer, filename="graph.png")
            embed.set_image(url="attachment://graph.png")

        def __generate_embed(self):
            embed = discord.Embed()
            if self.data_type == "latest":
                embed.title = "🌐 Global COVID-19 Information"
            else:
                country = self._info["locations"][0]
                flag = f":flag_{country['country_code'].lower()}:"
                embed.title = f"{flag} COVID-19 data for {country['country'].title()}"
                date_string = country["last_updated"]
                date_string.replace("Z", "+00:00")
                date = datetime.fromisoformat(date_string).strftime("%c")
                embed.set_footer(text=f"Last updated: {date}")
            embed.add_field(name="Confirmed", value=self.stats["confirmed"], inline=True)
            embed.add_field(name="Deaths", value=self.stats["deaths"], inline=True)
            embed.add_field(name="Recovered", value=self.stats["recovered"], inline=True)

            return embed

    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.url = "https://coronavirus-tracker-api.herokuapp.com/v2"

    async def fetch_country(self, q):
        url = f"{self.url}/locations?country={q}" if len(q) > 2 else f"{self.url}/locations?country_code={q}"
        async with self.session.get(url) as response:
            if response.status == 200:
                response = await response.json()
                return self.CovidResponse(response=response, data_type="country")

    async def fetch_latest(self):
        async with self.session.get(f"{self.url}/latest") as response:
            if response.status == 200:
                response = await response.json()
                return self.CovidResponse(response=response, data_type="latest")
            else:
                return self.CovidResponse(response=False, data_type=None)
