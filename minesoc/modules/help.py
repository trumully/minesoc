# help.py
# This extension is used for the custom help command of the bot.
import discord

from discord.ext import commands


class CustomHelpCommand(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        cmds = {i: [f"`{c.name}`" for c in await self.filter_commands(self.context.bot.get_cog(i).get_commands(), sort=True)] for i in self.context.bot.cogs
                if self.context.bot.get_cog(i).get_commands()}
        cmd_str = "\n".join([f"__**{i}**__\n{' '.join(cmds[i])}" for i in cmds if cmds[i]])
        embed = discord.Embed(title=f"{self.context.bot.user.name} Help",
                              description=f"Use `{self.clean_prefix}help [command] for more info on a command.`\n{cmd_str}",
                              color=self.context.bot.colors.help)
        await self.context.send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(title=f"{self.context.bot.user.name} Help",
                              description=f"```{self.get_command_signature(command)}```",
                              color=self.context.bot.colors.help)
        embed.add_field(name="Details:", value=command.help or "No details available.", inline=False)
        embed.add_field(name="Aliases:",
                        value=f"```{', '.join(command.aliases)}```" if command.aliases else "No aliases exist.",
                        inline=False)
        await self.context.send(embed=embed)

    async def send_group_help(self, group):
        embed = discord.Embed(title=f"{self.context.bot.user.name} Help",
                              description=f"Help for `{group.name}` command group."
                                          f"\nUse `{self.clean_prefix}help {group.name} [command]` "
                                          f"for more info on a command.",
                              color=self.context.bot.colors.help)
        embed.add_field(name="Details:", value=group.help or "No details available.", inline=False)
        embed.add_field(name="Available Subcommands:",
                        value=f"```\n{', '.join([command.name for command in group.commands])}\n```", inline=False)
        await self.context.send(embed=embed)

    async def send_cog_help(self, cog):
        embed = discord.Embed(title=f"{self.context.bot.user.name} Help",
                              description=f"{cog.name} commands.\n"
                                          f"Use `{self.clean_prefix}help [command]` for more info on a command.",
                              color=self.context.bot.colors.help)
        embed.add_field(name="Description:", value=cog.__doc__ if cog.__doc__ else "No description")
        embed.add_field(name="Commands:", value=f"```{', '.join(c.name for c in await self.filter_commands(cog.get_commands(), sort=True))}```")

    def get_command_signature(self, command):
        return "{0.clean_prefix}{1.qualified_name} {1.signature}".format(self, command)


class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._original_help_command = bot.help_command
        bot.help_command = CustomHelpCommand()
        bot.help_command.cog = self

    def cog_unload(self):
        self.bot.help_command = self._original_help_command


def setup(bot):
    bot.add_cog(Help(bot))
