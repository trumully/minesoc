import discord
import json
import time
import asyncio

from discord.ext import commands

LEVEL_COOLDOWN = 120


class Listeners(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cog_dict = {}
        for cog in self.bot.cogs:
            cog = self.bot.get_cog(cog)
            _commands = cog.get_commands()
            cog_name = cog.qualified_name
            self.cog_dict[f"{cog_name}"] = [c.name for c in _commands]

    def lvl_up(self, user):
        cur_xp = user['xp']
        cur_lvl = user['lvl']

        return bool(cur_xp >= round((4 * (cur_lvl ** 3) / 5)))

    async def bot_check(self, ctx):
        if not ctx.guild:
            return False

        if not self.bot.is_ready():
            await ctx.message.add_reaction("⏱️")
            return False

        return True

    @commands.Cog.listener()
    async def on_message(self, message):
        ctx = await self.bot.get_context(message)

        if message.author.bot or ctx.valid:
            return

        with open("guild_config.json", "r") as f:
            response = json.load(f)

        data = response.get(str(ctx.guild.id), {"disabled_commands": [], "lvl_msg": True, "lvl_system": True})

        do_lvl = data["lvl_system"]
        do_lvl_msg = data["lvl_msg"]

        if do_lvl:
            author = int(message.author.id)
            guild = int(message.guild.id)

            user = await self.bot.db.fetchrow("SELECT * FROM levels WHERE user_id = $1 AND guild_id = $2",
                                              author, guild)

            if not user:
                await self.bot.db.execute("INSERT INTO levels(user_id, guild_id, lvl, xp, cd, color, bg) "
                                          "VALUES($1, $2, 1, 0, $3, 'FFFFFF', 'default')", author, guild,
                                          time.time())

            user = await self.bot.db.fetchrow("SELECT * FROM levels WHERE user_id = $1 AND guild_id = $2", author,
                                              guild)

            xp = self.bot.xp_gain()

            if time.time() - user["cd"] >= LEVEL_COOLDOWN:
                await self.bot.db.execute("UPDATE levels SET xp = $1 WHERE user_id = $2 AND guild_id = $3",
                                          user["xp"] + xp, author, guild)

            if self.lvl_up(user):
                if do_lvl_msg:
                    await ctx.send(f"🆙 | **{message.author.name}** is now **Level {user['lvl'] + 1}**")
                await self.bot.db.execute("UPDATE levels SET lvl = $1 WHERE user_id = $2 AND guild_id = $3",
                                          user["lvl"] + 1, author, guild)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CheckFailure):
            pass

        elif isinstance(error, commands.DisabledCommand):
            await ctx.error(description=f"`{ctx.command}` is currently disabled. Try again later.")

        elif isinstance(error, (commands.BadArgument, commands.BadUnionArgument)):
            await ctx.error(
                description=f"A parse or conversion error occured with your arguments. Check your input and try "
                            f"again. If you need help, use `{ctx.prefix}help "
                            f"{ctx.command.qualified_name or ctx.command.name}`")

        elif isinstance(error, discord.Forbidden):
            await ctx.error(
                description="I'm unable to perform this action. "
                            "This could happen due to missing permissions for the bot.")

        elif isinstance(error, commands.NotOwner):
            await ctx.error(description="This command is only available to the bot developer.")

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.error(
                description=f"`{error.param.name}` is a required argument that is missing. For more help use "
                            f"`{ctx.prefix}help {ctx.command.qualified_name or ctx.command.name}`")

        elif isinstance(error, commands.MissingPermissions):
            await ctx.error(description="You're not allowed to use this command.")

        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.error(description="I don't have enough permissions to execute this command.")

        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.error(description="This command is not usable in DM's.")

        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.error(description=f"You're on cooldown! Retry in `{error.retry_after:,.2f}` seconds.")

        elif isinstance(error, commands.CommandNotFound):
            await ctx.message.add_reaction("❓")
            await asyncio.sleep(15)
            await ctx.message.remove_reaction(emoji="❓", member=ctx.guild.me)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        if guild.id in self.bot.guild_blacklist:
            try:
                embed = discord.Embed(color=self.bot.colors.red,
                                      description=f"Your guild / server tried to add me, but the ID is blacklisted. "
                                                  f"If you wish to know the reason, join the "
                                                  f"[Support server]({self.bot.invite_url})")
                await guild.owner.send(embed=embed)
                await guild.leave()
            except:
                pass
        else:
            with open("prefixes.json", "r") as f:
                prefixes = json.load(f)

            prefixes[str(guild.id)] = "m!"

            with open("prefixes.json", "w") as f:
                json.dump(prefixes, f, indent=4)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        with open("prefixes.json", "r") as f:
            prefixes = json.load(f)

        prefixes.pop(str(guild.id))

        with open("prefixes.json", "w") as f:
            json.dump(prefixes, f, indent=4)


def setup(bot):
    bot.add_cog(Listeners(bot))
