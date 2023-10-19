import json
import requests


class InsultManager:

    INSULT_URI = "https://evilinsult.com/generate_insult.php?lang=en&type=json"

    def __init__(self):
        self.insult_uri = InsultManager.INSULT_URI
        self.insult_count_map = {}

    def get_insult_as_text(self, sender_id: str, mention: str):
        if sender_id in self.insult_count_map.keys():
            if mention in self.insult_count_map[sender_id]:
                self.insult_count_map[sender_id][mention] += 1
            else:
                self.insult_count_map[sender_id][mention] = 1
        else:
            self.insult_count_map[sender_id] = {}
            self.insult_count_map[sender_id][mention] = 1
        print(self.insult_count_map)
        return requests.get(self.insult_uri).json()['insult']
