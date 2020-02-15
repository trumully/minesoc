import discord
import json
import aiosqlite
import time

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

        return True if cur_xp >= round((4 * (cur_lvl ** 3) / 5)) else False

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
            author_id = str(message.author.id)
            guild_id = str(message.guild.id)

            self.bot.db.row_factory = aiosqlite.Row
            async with self.bot.db.execute("SELECT user_id, guild_id, xp, lvl, cd FROM users "
                                           "WHERE user_id=:user AND guild_id=:guild",
                                           {"user": author_id, "guild": guild_id}) as cur:
                member = await cur.fetchone()

                xp_gain = self.bot.xp_gain()

                if not member:
                    await self.bot.db.execute("INSERT INTO users VALUES (:user, :guild, :xp, :lvl, :cd, :color, :bg)",
                                              {"user": author_id, "guild": guild_id, "xp": xp_gain, "lvl": 1,
                                               "cd": time.time(), "color": "ffffff", "bg": "default"})
                    await self.bot.db.commit()

                time_diff = time.time() - member["cd"]
                if time_diff >= LEVEL_COOLDOWN:
                    await cur.execute("UPDATE users SET xp=:xp, cd=:cd WHERE "
                                      "user_id=:user AND guild_id=:guild",
                                      {"xp": member["xp"] + xp_gain, "user": author_id, "guild": guild_id,
                                       "cd": time.time()})
                    await self.bot.db.commit()

                if self.lvl_up(member):
                    await cur.execute("UPDATE users SET lvl=:lvl WHERE user_id=:u_id AND guild_id=:g_id",
                                      {"lvl": member["lvl"] + 1, "u_id": author_id, "g_id": guild_id})
                    await self.bot.db.commit()
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
