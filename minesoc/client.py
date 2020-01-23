import discord
import asyncio
import logging
import os
import aiohttp
import aiosqlite
import json

from itertools import cycle
from dotenv import dotenv_values
from discord.ext.commands import Bot
from discord.ext import tasks
from os import listdir
from traceback import format_exc
from datetime import datetime
from pathlib import Path
from libneko.aggregates import Proxy
from .utils import logger, emojis, errors, context, config, api


ENV_DIR = Path(__file__).parent / ".env"


class Minesoc(Bot):
    def __init__(self, **kwargs):
        self.config = Proxy(dotenv_values(dotenv_path=ENV_DIR))
        super().__init__(command_prefix=self.config.PREFIX, description="General purpose bot. WIP",
                         owner_id=int(self.config.OWNER_ID),
                         **kwargs)

        self.loop = asyncio.get_event_loop()
        self.session = aiohttp.ClientSession()
        self.start_time = datetime.now()

        self.api = api.API(self)

        self.logger = logger.CustomLogger(name="minesoc",
                                          handler=logger.DiscordHandler(webhook_url=self.config.WEBHOOK_URL),
                                          level=logging.INFO)
        self._discord_logger = logger.CustomLogger(name="discord", level=logging.DEBUG)

        self._emojis = emojis.CustomEmojis()
        self.colors = config.ColorProxy()

    async def get_context(self, message, *, cls=None):
        return await super().get_context(message, cls=cls or context.MinesocContext)

    async def start(self):
        self.load_modules()
        await self._start()

    async def _start(self):
        await super().start(self.config.TOKEN)

    def load_modules(self):
        for module in listdir(f"minesoc/{self.config.MODULES_PATH}"):
            if module[-3:] == ".py" and module[:-3] != "__init__":
                try:
                    self.load_extension(f"minesoc.{self.config.MODULES_PATH}.{module.replace('.py', '')}")
                except Exception as ex:
                    self.logger.warning(f"Module {module.strip('.py')} failed to load due to the following error: "
                                        f"{type(ex).__name__}: {ex}")
        else:
            self.load_extension("jishaku")

    async def on_ready(self):
        self.dev_guild = self.get_guild(int(self.config.DEV_GUILD))
        self._emojis.fetch_emojis(self.dev_guild)
        self._owner = self.get_user(self.owner_id)
        self.logger.info(f"I'm ready! Logged in as: {self.user} ({self.user.id})")

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
