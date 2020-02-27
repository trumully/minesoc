import discord
import asyncio
import logging
import asyncpg
import json
import time
import traceback

from discord.ext import commands
from discord.ext.commands import Bot
from datetime import datetime
from pathlib import Path
from libneko.aggregates import Proxy
from minesoc.utils import logger, emojis, context, config, api, extras
from random import randint


class Minesoc(Bot):
    def __init__(self, **kwargs):
        self.config = config.File("config.json")
        super().__init__(command_prefix=self.config.default_prefix, description="General purpose bot. WIP.",
                         owner_id=int(self.config.owner), **kwargs)

        self.loop = asyncio.get_event_loop()
        self.start_time = time.time_ns()

        self.logger = logger.CustomLogger(name="minesoc",
                                          handler=logger.DiscordHandler(webhook_url=self.config.webhook_url),
                                          level=logging.INFO)
        self._discord_logger = logger.CustomLogger(name="discord", level=logging.INFO)

        self.path = Path(".")
        self.api = api.API(self)
        self.sqlschema = extras.SQLSchema()
        self._emojis = emojis.CustomEmojis()
        self.colors = config.ColorProxy()

        # self.da_id = self.config.deviantart_id
        # self.da_secret = self.config.deviantart_secret

        self.xp_values = Proxy(min=3, max=5)

        self.status = self.loop.create_task(self.change_status())

    async def start(self):
        await self.connect_to_database()
        self.load_modules()
        await self._start()

    async def _start(self):
        await super().start(self.config.token)

    async def close(self):
        try:
            await self.db.close()
        finally:
            await super().close()

    async def get_context(self, message, *, cls=None):
        return await super().get_context(message, cls=cls or context.MinesocContext)

    async def connect_to_database(self):
        try:
            self.db = await asyncpg.create_pool(**self.config.postgres)
            await self.db.execute(self.sqlschema.read("schema.sql"))
            self.logger.info("Connected to database.")
            await self.load_blacklist()
        except Exception as e:
            self.logger.warning("An error occurred connecting to the database", exc_info=e)

    async def load_blacklist(self):
        try:
            self.user_blacklist = [u["id"] for u in (await self.db.fetch("SELECT id FROM user_blacklist"))]
            self.guild_blacklist = [g["id"] for g in (await self.db.fetch("SELECT id FROM guild_blacklist"))]
        except Exception as e:
            self.logger.error("Blacklist could not be loaded.", exc_info=e)
        else:
            self.logger.info(
                f"Initialized blacklist. {len(self.guild_blacklist)} guilds and {len(self.user_blacklist)} users "
                f"blacklisted.")

    def xp_gain(self):
        return randint(self.xp_values.min, self.xp_values.max)

    def load_modules(self):
        for module in (self.path / "minesoc" / self.config.modules_path).iterdir():
            if module.suffix == ".py" and module.name != "__init__.py":
                try:
                    self.load_extension(f"minesoc.{self.config.modules_path}.{module.name[:-3]}")
                except Exception as ex:
                    self.logger.warning(f"Module {module.name[:-3]} failed to load due to the following error: ",
                                        exc_info=ex.with_traceback(ex.__traceback__))
        else:
            self.load_extension("jishaku")

    async def on_ready(self):
        self.dev_guild = self.get_guild(int(self.config.dev_guild))
        self._emojis.fetch_emojis(self.dev_guild)
        self._owner = self.get_user(self.owner_id)

        self.logger.info(f"I'm ready! Logged in as: {self.user} ({self.user.id})")

    async def change_status(self):
        await self.wait_until_ready()
        status_list = iter([f"{len(self.guilds)} guilds", f"{len(self.users)} users", "you"])
        while not self.is_closed():
            status = next(status_list, "m!help")
            if status == "m!help":
                status_list = iter([f"{len(self.guilds)} guilds", f"{len(self.users)} users", "you"])
            await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching,
                                                                 name=status))
            await asyncio.sleep(600)

    def get_owner(self):
        return self.get_user(self.owner_id)

    def format_datetime(self, time: datetime):
        return time.strftime("%d %B %Y, %X")

    def measure_time(self, start, end):
        duration = int(end - start)
        return self.seconds_to_hms(duration)

    def seconds_to_hms(self, seconds):
        seconds = seconds % (24 * 3600)
        hour = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60
        if hour == 0:
            return "%02d:%02d" % (minutes, seconds)
        return "%d:%02d:%02d" % (hour, minutes, seconds)

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
    def custom_emojis(self):
        return self._emojis
