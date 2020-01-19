from discord.ext.commands import CommandError


class InvalidSubCommand(CommandError):
    pass


class OnlyDevGuild(CommandError):
    pass


class APIError(CommandError):
    pass


class KsoftError(CommandError):
    pass
