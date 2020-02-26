from discord.ext.commands import CommandError


class DisabledCommand(CommandError):
    pass


class OnlyDevGuild(CommandError):
    pass
