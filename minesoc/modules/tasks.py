import discord

from discord.ext import commands, tasks
from minesoc.utils import emojis
from itertools import cycle


class Tasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.status = cycle([f"{len(self.bot.guilds)} guilds", f"{len(self.bot.users)} users", "m!help"])
        self.change_status.start()
        self.refresh_emoji.start()

    def cog_unload(self):
        self.change_status.stop()
        self.refresh_emoji.stop()

    @tasks.loop(minutes=10)
    async def change_status(self):
        await self.bot.change_presence(activity=discord.Activity(
            type=discord.ActivityType.listening,
            name=f"{next(self.status)}"))

    @tasks.loop(seconds=60)
    async def refresh_emoji(self):
        try:
            self.bot._emojis.fetch_emojis(self.bot.dev_guild)
            self.bot._emojis.reinit()
        except Exception as e:
            print(e)

    @change_status.before_loop
    @refresh_emoji.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(Tasks(bot))
