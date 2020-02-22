class SQLSchema:
    def __init__(self):
        self.cache = {}

    def read(self, file):
        if file not in self.cache:
            with open("minesoc/" + file, "r") as f:
                self.cache[file] = f.read()

        return self.cache[file]
