"""Cofres de recompensa: estado, tipo e interacción lógica."""

class Chest:
    CLOSED = "closed"
    OPEN = "open"

    def __init__(self, chest_type="common", x=0.0, y=0.0):
        self.chest_type = chest_type
        self.x = float(x)
        self.y = float(y)
        self.state = self.CLOSED
        self.reward_claimed = False

    @property
    def is_open(self):
        return self.state == self.OPEN

    def open(self):
        if self.is_open or self.reward_claimed:
            return False
        self.state = self.OPEN
        self.reward_claimed = True
        return True
