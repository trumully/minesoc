import json
from libneko.aggregates import Proxy


class File(Proxy):
    def __init__(self, path):
        with open(path, "r") as f:
            super().__init__(json.loads(f.read()))


class ColorProxy(Proxy):
    def __init__(self):
        with open("colors.json", "r") as f:
            super().__init__(json.loads(f.read()))

    def __getattribute__(self, name):
        return int(super().__getattribute__(name), 16) + 0x200

    def __getitem__(self, item):
        return self.__getattribute__(item)
