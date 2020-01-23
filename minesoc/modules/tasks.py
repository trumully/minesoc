import discord

from discord.ext import commands, tasks
from itertools import cycle

status = cycle(["C418", "Stal", "LOOΠΔ"])


class Tasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.change_status.start()

    def cog_unload(self):
        self.change_status.stop()

    @tasks.loop(seconds=60)
    async def change_status(self):
        await self.bot.change_presence(activity=discord.Activity(
            type=discord.ActivityType.listening,
            name=f"{next(status)} | m!help | {len(self.bot.guilds)} servers"))

    @change_status.before_loop
    async def before_change_status(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(Tasks(bot))
