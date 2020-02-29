from discord.ext import commands


def is_owner_or_has_permissions(**perms):
    def predicate(ctx):
        permissions = ctx.channel.permissions_for(ctx.author)

        missing = [perm for perm, value in perms.items() if getattr(permissions, perm, None) != value]

        if not missing:
            return True
        else:
            if ctx.bot.is_owner(ctx.author):
                return True

        raise commands.MissingPermissions(missing)

    return commands.check(predicate)
