import json
import logging
import os
from socket import gethostname

import requests


class DiscordHandler(logging.Handler):
    """
    A custom handler class which sends logging records, to a webhook.
    """

    def __init__(self, webhook_url):
        logging.Handler.__init__(self)

        if not os.path.isdir("minesoc/logs"):
            os.mkdir("minesoc/logs")

        if not webhook_url:
            raise ValueError("A webhook url must be given!")

        self._webhook_url = webhook_url
        self._agent = gethostname()
        self._header = self._create_header()

        self._color_table = {
            "ERROR": 0xe74c3c,
            "WARNING": 0xe67e22,
            "INFO": 0x3498db,
            "DEBUG": 0x1abc9c
        }

        self._emoji_table = {
            "ERROR": "🚫",
            "WARNING": "⚠️",
            "INFO": "ℹ️",
            "DEBUG": "🤔",
        }

    def _create_header(self):
        return {
            'User-Agent': self._agent,
            "Content-Type": "application/json"
        }

    def _post_webhook(self, message, record):
        embed = {
            "embeds": [
                {
                    "title": f"{self._emoji_table[record.levelname]} {record.levelname.title()}",
                    "description": message,
                    "color": self._color_table[record.levelname]
                }
            ]
        }

        try:
            requests.post(self._webhook_url, headers=self._header, data=json.dumps(embed))
        except Exception as ex:
            print(ex)

    def handle(self, record):
        try:
            message = self.format(record)
            self._post_webhook(message=f"```\n{message}\n```", record=record)
        except Exception:
            self.handleError(record)


class CustomLogger(logging.Logger):
    """
    A custom logger class to make initalizing loggers easier (even tho it's easy af).
    """

    def __init__(self, level, name, handler=None, directory="logs"):
        if not os.path.isdir(directory):
            os.mkdir(directory)

        if name == "discord":
            self = logging.getLogger("discord")
        else:
            super().__init__(name, level)

        self.setLevel(level)
        self._logging_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        filehandler = logging.FileHandler(filename=f"{directory}/{name}.log", encoding="utf-8", mode="w")
        filehandler.setFormatter(self._logging_format)

        if not isinstance(handler, DiscordHandler):
            self.info("You're not using the custom handler class.")
        else:
            handler.setLevel(level)
            handler.setFormatter(self._logging_format)
            self.addHandler(handler)

        self.addHandler(filehandler)
