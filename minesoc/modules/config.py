import discord
import json

from discord.ext import commands
from minesoc.utils import config

blacklist = ["Help", "Config", "Listeners"]


class Config(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cog_dict = {}
        for cog in self.bot.cogs:
            cog = self.bot.get_cog(cog)
            cog_name = cog.qualified_name
            if cog_name not in blacklist:
                _commands = cog.get_commands()
                self.cog_dict[f"{cog_name}"] = [c.name for c in _commands]

    @commands.group()
    @commands.has_permissions(manage_guild=True)
    async def config(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Invalid subcommand")

    @config.command()
    async def enable(self, ctx, *, option: str):
        option = option.lower()
        to_enable = None
        is_cog = False

        for cog in self.cog_dict:
            if option.casefold() == cog.casefold():
                to_enable = cog
                is_cog = True
            else:
                for command in self.cog_dict[cog.title()]:
                    if option.casefold() == command.casefold():
                        to_enable = command

        if to_enable is None:
            return await ctx.send("Could not find that cog/command.")
        else:
            with open("config.json", "r") as f:
                res = json.load(f)

            try:
                data = res[str(ctx.guild.id)]
            except KeyError:
                res[str(ctx.guild.id)] = {"disabled_commands": [], "lvl_msg": True, "lvl_system": True}
                data = res[str(ctx.guild.id)]

            embed = discord.Embed(color=discord.Color.green())

            if is_cog:
                title = "Enabled the X cog."
                error = "X cog is already enabled!"
                enabled = [c for c in self.cog_dict[to_enable.title()]]
            else:
                title = "Enabled the X command."
                error = "X command is already enabled!"
                enabled = [to_enable.lower()]

            any_enabled = None
            for i in enabled:
                if i in data["disabled_commands"]:
                    data["disabled_commands"].remove(i)
                    any_enabled = True
            if to_enable == "Levels":
                data["lvl_msg"] = True
                data["lvl_system"] = True

            if any_enabled:
                embed.title = title.replace("X", f"`{to_enable}`")
            else:
                embed.title = error.replace("X", f"`{to_enable}`")

            with open("config.json", "w") as f:
                json.dump(res, f, indent=4)

            await ctx.send(embed=embed)

    @config.command()
    async def disable(self, ctx, *, option: str):
        option = option.lower()
        to_disable = None
        is_cog = False

        for cog in self.cog_dict:
            if option.casefold() == cog.casefold():
                to_disable = cog
                is_cog = True
            else:
                for command in self.cog_dict[cog.title()]:
                    if option.casefold() == command.casefold():
                        to_disable = command

        if to_disable is None:
            return await ctx.send("Could not find that cog/command.")
        else:
            with open("config.json", "r") as f:
                res = json.load(f)

            try:
                data = res[str(ctx.guild.id)]
            except KeyError:
                res[str(ctx.guild.id)] = {"disabled_commands": [], "lvl_msg": True, "lvl_system": True}
                data = res[str(ctx.guild.id)]

            embed = discord.Embed(color=discord.Color.red())

            if is_cog:
                title = "Disabled the X cog."
                error = "X cog is already disabled!"
                disabled = [c for c in self.cog_dict[to_disable.title()]]
            else:
                title = "Disabled the X command."
                error = "X command is already disabled!"
                disabled = [to_disable.lower()]

            any_disabled = False
            for i in disabled:
                if i not in data["disabled_commands"]:
                    data["disabled_commands"].append(i)
                    any_disabled = True
            if to_disable == "Levels":
                data["lvl_msg"] = False
                data["lvl_system"] = False

            if any_disabled:
                embed.title = title.replace("X", f"`{to_disable}`")
            else:
                embed.title = error.replace("X", f"`{to_disable}`")

            with open("config.json", "w") as f:
                json.dump(res, f, indent=4)

            await ctx.send(embed=embed)

    @config.command()
    async def lvl_msg(self, ctx):
        with open("config.json", "r") as f:
            res = json.load(f)

        try:
            data = res[str(ctx.guild.id)]
        except KeyError:
            res[str(ctx.guild.id)] = {"disabled_commands": [], "lvl_msg": True, "lvl_system": True}
            data = res[str(ctx.guild.id)]

        data["lvl_msg"] = not data["lvl_msg"]

        embed = discord.Embed()

        embed.title = "Level up message disabled" if not data["lvl_msg"] else "Level up message enabled"
        embed.colour = discord.Color.red() if not data["lvl_msg"] else discord.Color.green()

        with open("config.json", "w") as f:
            json.dump(res, f, indent=4)

        await ctx.send(embed=embed)

    @commands.command(name="prefix")
    @commands.has_permissions(manage_guild=True)
    async def changeprefix(self, ctx, prefix: str):
        embed = discord.Embed()
        if len(prefix) >= 15:
            embed.colour = discord.Color.red()
            embed.title = "That prefix is too long!"
        else:
            with open("prefixes.json", "r") as f:
                prefixes = json.load(f)

            embed.colour = discord.Color.green()
            embed.title = f"Changed prefix to `{prefix}`"
            prefixes[str(ctx.guild.id)] = prefix

            with open("prefixes.json", "w") as f:
                json.dump(prefixes, f, indent=4)

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Config(bot))
