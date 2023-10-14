from sleeper.model import (
    User,
    Transaction,
    DraftPick,
    Player
)
from models.TradeConsenter import TradeConsenter


class Trade:

    def __init__(self, consenters: [str, TradeConsenter], transaction_id: str, last_udpated: int):
        self.consenters = consenters
        self.transaction_id = transaction_id
        self.last_updated = last_udpated
