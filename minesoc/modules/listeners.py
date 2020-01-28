import discord
import json
import aiosqlite
import time

from discord.ext import commands
from random import randint


class Listeners(commands.Cog):
    def __init__(self, bot: commands.Bot):
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

        res = True if cur_xp >= round((4 * (cur_lvl ** 3) / 5)) else False
        return res

    async def bot_check(self, ctx):
        if not ctx.guild:
            return True

        if not self.bot.is_ready():
            await ctx.message.add_reaction("⏱️")
            return False

        return True

    @commands.Cog.listener()
    async def on_message(self, message):
        ctx = await self.bot.get_context(message)

        if message.author.bot or ctx.valid:
            return

        with open("config.json", "r") as f:
            response = json.load(f)

        try:
            data = response[str(ctx.guild.id)]
        except KeyError:
            response[str(ctx.guild.id)] = {"disabled_commands": [], "lvl_msg": True, "lvl_system": True}
            data = response[str(ctx.guild.id)]

        do_lvl = data["lvl_system"]
        do_lvl_msg = data["lvl_msg"]

        if do_lvl:
            author_id = str(message.author.id)
            guild_id = str(message.guild.id)
            color = str(message.author.color).lstrip("#")

            async with aiosqlite.connect("level_system.db") as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT user_id, guild_id, xp, lvl, cd FROM users "
                                      "WHERE user_id=:user AND guild_id=:guild",
                                      {"user": author_id, "guild": guild_id}) as cur:
                    member = await cur.fetchone()

                    xp_gain = randint(1, 7)

                    if not member:
                        await db.execute("INSERT INTO users VALUES (:user, :guild, :xp, :lvl, :cd, :color)",
                                         {"user": author_id, "guild": guild_id, "xp": xp_gain, "lvl": 1,
                                          "cd": time.time(), "color": color})
                        await db.commit()
                    else:
                        time_diff = time.time() - member["cd"]
                        if time_diff >= 120:
                            await cur.execute("UPDATE users SET xp=:xp, cd=:cd WHERE "
                                              "user_id=:user AND guild_id=:guild",
                                              {"xp": member["xp"] + xp_gain, "user": author_id, "guild": guild_id,
                                               "cd": time.time()})
                            await db.commit()

                    if self.lvl_up(member):
                        await cur.execute("UPDATE users SET lvl=:lvl WHERE user_id=:u_id AND guild_id=:g_id",
                                          {"lvl": member["lvl"] + 1, "u_id": author_id, "g_id": guild_id})
                        await db.commit()
                        if do_lvl_msg:
                            await ctx.send(f"🆙 | **{self.bot.get_user(member['user_id']).name}** "
                                           f"leveled up to **Level {member['lvl'] + 1}**!")

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
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
