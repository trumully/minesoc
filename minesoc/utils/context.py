from discord.ext import commands
import discord
import asyncio


class MinesocContext(commands.Context):
    """Custom Context"""
    async def error(self, **kwargs):
        kwargs["description"] = f"{self.bot.custom_emojis.cross} {kwargs['description']}"
        embed = discord.Embed(color=discord.Color.red(), **kwargs)
        embed.set_footer(
            text=f"Command executed by: {self.author} | {self.prefix}help {self.command.name} for detailed help",
            icon_url=self.author.avatar_url_as(static_format="png"))
        return await self.send(embed=embed)

    async def info(self, description: str):
        embed = discord.Embed(color=discord.Color.blue(), description=f"ℹ️ {description}")
        embed.set_footer(text=f"Command executed by: {self.author}",
                         icon_url=self.author.avatar_url_as(static_format="png"))
        return await self.send(embed=embed)

    async def success(self, description: str):
        embed = discord.Embed(color=discord.Color.green(), description=f"{self.bot.custom_emojis.green_tick} {description}")
        embed.set_footer(text=f"Command executed by: {self.author}",
                         icon_url=self.author.avatar_url_as(static_format="png"))
        return await self.send(embed=embed)

    def colors(self, name):
        pass

    def switch(self, boolean: bool):
        options = {True: self.bot.custom_emojis.on, False: self.bot.custom_emojis.off}
        return options[boolean]

    async def confirm(self, message: discord.Message, timeout=30):
        REACTIONS = [self.bot.custom_emojis.green_tick, self.bot.custom_emojis.red_tick]

        for r in REACTIONS:
            await message.add_reaction(r)

        def _check(reaction: discord.Reaction, user: discord.User):
            return user.id == self.author.id and message.id == reaction.message.id and str(reaction) in REACTIONS

        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=timeout, check=_check)
        except asyncio.TimeoutError:
            await message.delete()
            await self.error(description="Action cancelled! You took too long.")
        else:
            reaction = str(reaction)

            if reaction == self.bot.custom_emojis.green_tick:
                await message.delete()
                return True
            elif reaction == self.bot.custom_emojis.red_tick:
                await message.delete()
                await self.error(description="Action declined.")
                return False
