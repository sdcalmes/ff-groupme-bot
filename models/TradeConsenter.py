from sleeper.model import (
    DraftPick,
    Player
)


class TradeConsenter:

    def __init__(self, draft_picks: list[DraftPick], players: list[Player], faab: int):
        self.draft_picks = draft_picks
        self.players = players
        self.faab = faab
