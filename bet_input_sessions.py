class BetInputSession:
    def __init__(self, telegram_id: int, matches: tuple[str, ...]):
        self.user_id = telegram_id
        self.matches: tuple[str, ...] = matches
        self.match = None

    def next_match(self):
        if not self.match:
            self.match = self.matches[0]
            return self.match

        i = self.matches.index(self.match)
        if i == len(self.matches) - 1:
            return
        else:
            self.match = self.matches[i + 1]
        return self.match
