

class Sidebet:

    def __init__(self, owner_a: str, owner_b: str, consequence: str, details: str):
        self.owner_a = owner_a
        self.owner_b = owner_b
        self.consequence = consequence
        self.details = details

    def __str__(self):
        return f'\nOwner A: {self.owner_a}\nOwner B: {self.owner_b}\nConsequence: {self.consequence}\nDetails: {self.details}'