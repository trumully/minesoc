import discord
import asyncio
import logging
import aiosqlite
import json
import deviantart
import aiohttp
import time

from discord.ext import commands
from discord.ext.commands import Bot
from datetime import datetime
from pathlib import Path
from libneko.aggregates import Proxy
from minesoc.utils import logger, emojis, context, config, api
from random import randint


class Minesoc(Bot):
    def __init__(self, **kwargs):
        self.config = config.File("config.json")
        super().__init__(command_prefix=self.get_prefix, description="General purpose bot. WIP.",
                         owner_id=int(self.config.owner), **kwargs)

        self.loop = asyncio.get_event_loop()
        self.start_time = time.time_ns()

        self.logger = logger.CustomLogger(name="minesoc",
                                          handler=logger.DiscordHandler(webhook_url=self.config.webhook_url),
                                          level=logging.INFO)
        self._discord_logger = logger.CustomLogger(name="discord", level=logging.DEBUG)

        self.path = Path(__file__).parent
        self.api = api.API(self)
        self._emojis = emojis.CustomEmojis()
        self.colors = config.ColorProxy()

        self.xp_values = Proxy({"min": 3, "max": 5})

        self.status = self.loop.create_task(self.change_status())

    async def get_context(self, message, *, cls=None):
        return await super().get_context(message, cls=cls or context.MinesocContext)

    async def connect_to_database(self):
        try:
            self.db = await aiosqlite.connect("database.db")
            self.logger.info("Connected to database.")
        except Exception as e:
            self.logger.warning("An error occurred connecting to the database", exc_info=e)

    async def start(self):
        await self.connect_to_database()
        self.load_modules()
        await self._start()

    async def _start(self):
        await super().start(self.config.TOKEN)

    async def close(self):
        try:
            await self.db.close()
        finally:
            await super().close()

    async def get_prefix(self, message):
        with open("prefixes.json", "r") as f:
            prefixes = json.load(f)

        prefixes.get(str(message.guild.id, self.config.PREFIX))

        return commands.when_mentioned_or(prefixes[str(message.guild.id)])(self, message)

    async def on_message(self, message):
        if isinstance(message.channel, discord.DMChannel):
            return

        ctx = await self.get_context(message)

        with open("guild_config.json", "r") as f:
            response = json.load(f)

        data = response.get(str(ctx.guild.id), {"disabled_commands": [], "lvl_msg": True, "lvl_system": True})

        if ctx.valid:
            if ctx.command.name in data["disabled_commands"]:
                raise commands.DisabledCommand(message="Tried to invoke disabled command")
            else:
                await self.process_commands(message)

    def xp_gain(self):
        return randint(self.xp_values.min, self.xp_values.max)

    def load_modules(self):
        for module in Path(f"minesoc/{self.config.MODULES_PATH}").iterdir():
            module = str(module)
            if module[-3:] == ".py" and module[:-3] != "__init__":
                try:
                    self.load_extension(f"minesoc.{self.config.modules_path}.{module.replace('.py', '')}")
                except Exception as ex:
                    self.logger.warning(f"Module {module.strip('.py')} failed to load due to the following error: "
                                        f"{type(ex).__name__}: {ex}")
        else:
            self.load_extension("jishaku")

    async def on_ready(self):
        self.dev_guild = self.get_guild(int(self.config.dev_guild))
        self._emojis.fetch_emojis(self.dev_guild)
        self._owner = self.get_user(self.owner_id)
        self.logger.info(f"I'm ready! Logged in as: {self.user} ({self.user.id})")

    async def change_status(self):
        await self.wait_until_ready()
        status_list = iter([f"{len(self.guilds)} guilds", f"{len(self.users)} users"])
        while not self.is_closed():
            status = next(status_list, "m!help")
            if status == "m!help":
                status_list = iter([f"{len(self.guilds)} guilds", f"{len(self.users)} users"])
            await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,
                                                                 name=status))
            await asyncio.sleep(600)

    async def get_da(self):
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                self.da = deviantart.Api(self.config.DEVIANTART_CLIENT_ID, self.config.DEVIANTART_CLIENT_SECRET)
                self.da_access_token = self.da.access_token
            except Exception as e:
                self.logger.warning("Failed to generate DeviantArt access token", exc_info=e)

            await asyncio.sleep(3600)

    def get_owner(self):
        return self.get_user(self.owner_id)

    def format_datetime(self, time: datetime):
        return time.strftime("%d %B %Y, %X")

    def oauth(self, client_id: int = None):
        client_id = client_id or self.user.id
        return discord.utils.oauth_url(client_id)

    @property
    def invite_url(self):
        return "https://discord.gg/mPYYSCp"

    @property
    def owner(self):
        if self._owner:
            return self._owner
        else:
            return self.get_owner()

    @property
    def emojis(self):
        return self._emojis
