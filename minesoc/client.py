import discord
import asyncio
import logging
import os
import aiohttp
import aiosqlite
import json

from dotenv import dotenv_values
from discord.ext import commands
from discord.ext.commands import Bot
from os import listdir
from traceback import format_exc
from datetime import datetime
from pathlib import Path
from libneko.aggregates import Proxy
from minesoc.utils import logger, emojis, context, config, api
from itertools import cycle


ENV_DIR = Path(__file__).parent / ".env"


class Minesoc(Bot):
    def __init__(self, **kwargs):
        self.config = Proxy(dotenv_values(dotenv_path=ENV_DIR))
        super().__init__(command_prefix=self.get_prefix, description="General purpose bot. WIP",
                         owner_id=int(self.config.OWNER_ID), **kwargs)

        self.loop = asyncio.get_event_loop()
        self.start_time = datetime.now()

        self.logger = logger.CustomLogger(name="minesoc",
                                          handler=logger.DiscordHandler(webhook_url=self.config.WEBHOOK_URL),
                                          level=logging.INFO)
        self._discord_logger = logger.CustomLogger(name="discord", level=logging.DEBUG)

        self.api = api.API(self)
        self._emojis = emojis.CustomEmojis()
        self.colors = config.ColorProxy()

        self.status = self.loop.create_task(self.change_status())

    async def get_context(self, message, *, cls=None):
        return await super().get_context(message, cls=cls or context.MinesocContext)

    async def start(self):
        self.load_modules()
        await self._start()

    async def _start(self):
        await super().start(self.config.TOKEN)

    async def close(self):
        try:
            await self._conn.close()
        finally:
            await super().close()

    async def get_prefix(self, message):
        with open("prefixes.json", "r") as f:
            prefixes = json.load(f)

        try:
            data = prefixes[str(message.guild.id)]
        except KeyError:
            prefixes[str(message.guild.id)] = self.config.PREFIX

        return commands.when_mentioned_or(prefixes[str(message.guild.id)])(self, message)

    async def on_message(self, message):
        ctx = await self.get_context(message)

        with open("config.json", "r") as f:
            response = json.load(f)

        try:
            data = response[str(ctx.guild.id)]
        except KeyError:
            response[str(ctx.guild.id)] = {"disabled_commands": [], "lvl_msg": True, "lvl_system": True}
            data = response[str(ctx.guild.id)]

        disabled_commands = data["disabled_commands"]

        if ctx.valid:
            if ctx.command.name in disabled_commands:
                raise commands.DisabledCommand(message="Tried to invoke disabled command")
            else:
                await self.process_commands(message)

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

    async def change_status(self):
        await self.wait_until_ready()
        status = cycle([f"{len(self.guilds)} guilds", f"{len(self.users)} users", "m!help"])
        while not self.is_closed():
            await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,
                                                                 name=f"{next(status)}"))
            await asyncio.sleep(60*10)

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
