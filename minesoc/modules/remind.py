import dateparser
import aiosqlite
import discord

from discord.ext import commands, tasks
from datetime import datetime, timezone, timedelta
from libneko import pag


@pag.embed_generator(max_chars=2048, provides_numbering=False)
def reminders_factory(paginator, page, page_index):
    return discord.Embed(color=discord.Color.blurple(), description=page,
                         title="📆 Reminders").set_footer(text=f"Page {page_index + 1} / {len(paginator)}")


def seconds_to_hms(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60

    res = ""
    if hour > 0:
        res += f"{round(hour) if hour >= 1 else ''}{' hours' if hour > 1 else 'hour'}, "
    if minutes > 0:
        res += f"{round(minutes) if minutes >= 1 else ''}{' minutes' if minutes > 1 else ' minute'}, "
    if seconds > 0:
        res += f"{round(seconds) if seconds >= 1 else ''}{' seconds' if seconds > 1 else ' second'}"

    return res


REMINDER_CAP = 5


class RemindMe(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.bot.loop.create_task(self.create_table())
        self.check_reminder.start()

    def cog_unload(self):
        self.check_reminder.cancel()

    async def create_table(self):
        await self.bot.wait_until_ready()

        await self.bot.db.execute("CREATE TABLE IF NOT EXISTS remindme(id INTEGER PRIMARY KEY AUTOINCREMENT, user INTEGER, title TEXT, date TEXT, total REAL, repeat INTEGER)")

    @tasks.loop(seconds=1)
    async def check_reminder(self):
        await self.bot.wait_until_ready()

        self.bot.db.row_factory = aiosqlite.Row
        async with self.bot.db.execute("SELECT id, user, title, date, total, repeat FROM remindme") as cursor:
            async for row in cursor:
                diff = round((datetime.utcnow() - datetime.strptime(row["date"].split(".")[0], "%Y-%m-%d %H:%M:%S")).total_seconds())
                if diff == 0:
                    await self.send_reminder(row["user"], row["date"], row["title"], row["total"], row["repeat"])
                    if row["repeat"] == 0:
                        await self.remove_reminder(row["id"])
                    else:
                        date = datetime.strptime(row["date"].split(".")[0], "%Y-%m-%d %H:%M:%S") + timedelta(seconds=round(row["total"]))
                        await cursor.execute("UPDATE remindme SET date=:date WHERE id=:id",
                                             {"date": str(date), "id": row["id"]})

    async def create_reminder(self, ctx, time, title: str = "Reminder!", repeat: int = 0):
        user = int(ctx.author.id)
        time = dateparser.parse(time)
        time = datetime.utcfromtimestamp(time.timestamp())

        if not bool(time):
            return False

        total = (datetime.utcnow() - time).total_seconds()
        if total <= 0:
            total = abs(total)
        total = round(total)
        time = str(time).split(".")[0]

        res = bool(await self.bot.db.execute("INSERT INTO remindme(user, title, date, total, repeat) VALUES (:user, :title, :date, :total, :repeat)",
                                             {"user": user, "title": title, "date": str(time), "total": total, "repeat": repeat}))
        return res

    async def remove_reminder(self, uuid):
        async with self.bot.db.execute(f"SELECT * FROM remindme WHERE id={uuid}") as cursor:
            await cursor.execute(f"DELETE FROM remindme WHERE id={uuid}")
            if cursor.rowcount < 1:
                return False
            return True

    async def get_reminder(self, user):
        async with self.bot.db.execute(f"SELECT * FROM remindme WHERE user={user}") as cursor:
            reminder = await cursor.fetchone()
            if reminder:
                return reminder

    async def send_reminder(self, user, date: datetime, title, total, repeat):
        embed = discord.Embed(title="Reminder!", timestamp=datetime.strptime(date, "%Y-%m-%d %H:%M:%S"))
        embed.description = f"{title if title else 'Reminder!'}"
        if repeat == 1:
            embed.set_footer(text=f"{f'Repeats every {seconds_to_hms(round(total))}' if repeat == 1 else ''}")
        member = self.bot.get_user(user)

        await member.send(embed=embed)

    @commands.group(name="remindme")
    async def remind(self, ctx):
        """Reminder management."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @remind.command(name="create", aliases=["new"])
    async def remind_create(self, ctx, time, reason: str = None, repeat: int = 0):
        """
        Create a new reminder.
        Example usage:
        `create "in 5 seconds"` will DM you a reminder
        `create "tomorrow" "Do a thing!"` will DM you "Do a thing!" in 24 hours
        `create "1 hour" "Hourly reminder" 1` will DM you "Hourly reminder" every hour
        """
        if await self.create_reminder(ctx, time, reason, repeat):
            await ctx.message.add_reaction(self.bot.emojis.greenTick)
        else:
            await ctx.message.add_reaction(self.bot.emojis.redTick)
            await ctx.error(description="An error has occurred!")

    @remind.command(name="remove", aliases=["delete"])
    async def remind_remove(self, ctx, *, title):
        user = int(ctx.author.id)
        async with self.bot.db.execute("SELECT * FROM remindme WHERE user=:user AND title=:title", {"user": user, "title": title}) as c:
            reminder = await c.fetchone()

        if await self.remove_reminder(reminder["id"]):
            await ctx.message.add_reaction(self.bot.emojis.greenTick)
        else:
            await ctx.message.add_reaction(self.bot.emojis.redTick)
            await ctx.error(description="Failed to delete! This may be because reminder does not exist or you are not"
                                        "the owner.")

    @remind.command(name="list")
    async def remind_list(self, ctx, member: discord.Member = None):
        member = member if member else ctx.author

        self.bot.db.row_factory = aiosqlite.Row
        async with self.bot.db.execute(f"SELECT title, date, repeat, total FROM remindme WHERE user={member.id}") as cursor:
            result = await cursor.fetchall()
            reminders = [dict(row) for row in result]

        if reminders:
            nav = pag.EmbedNavigatorFactory(max_lines=15, factory=reminders_factory)
            for index, value in enumerate(reminders):
                total = round(value.get("total"))
                time = round((datetime.strptime(value.get("date"), "%Y-%m-%d %H:%M:%S") - datetime.utcnow()).total_seconds())
                repeat = value.get("repeat") == 1
                nav.add_line(f"{index + 1}. **{value.get('title')}** "
                             f"{f'every `{seconds_to_hms(total)}`' if repeat else f'in `{seconds_to_hms(time)}`'}")
            else:
                nav.start(ctx)
        else:
            await ctx.info(
                "You don't have any reminders." if member == ctx.author else f"{member.mention} has no reminders")


def setup(bot):
    bot.add_cog(RemindMe(bot))
