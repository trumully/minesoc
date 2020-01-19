from libneko.aggregates import Proxy
from discord import Guild, Emoji


class CustomEmojis(Proxy):
    def __init__(self):
        self.is_empty = True
        self.guild = None

    def fetch_emojis(self, guild: Guild):
        self.guild = guild

        if not isinstance(guild, Guild):
            raise TypeError(f"Expected discord.Guild, got {type(guild).__name__}")

        init_dict = dict()
        for emoji in guild.emojis:
            init_dict[emoji.name] = str(emoji)
        else:
            self.is_empty = False
            super().__init__(init_dict)

    def set_emoji(self, emoji: Emoji):
        super().__setitem__(emoji.name, str(emoji))

    def remove_emoji(self, emoji: Emoji):
        super().__delitem__(emoji.name)

    def reinit(self):
        self.fetch_emojis(self.guild)
