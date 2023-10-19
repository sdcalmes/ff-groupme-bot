import unittest
from insults.InsultManager import InsultManager


class TestInsultManager(unittest.TestCase):

    def test_uri(self):
        insult_manager = InsultManager()
        self.assertEqual(insult_manager.insult_uri,
                         "https://evilinsult.com/generate_insult.php?lang=en&type=json", "Incorrect insults API URI")

    def test_get_insult_as_text(self):
        insult_manager = InsultManager()
        insult = insult_manager.get_insult_as_text('fake_id', 'fake_mention_id')
        self.assertEqual(type(insult), str, "Returned insult is not a string!")
        self.assertGreater(len(insult), 0, "Insult string was not > 0 characters!")
        self.assertEqual(len(insult_manager.insult_count_map), 1)
        self.assertEqual(insult_manager.insult_count_map, {"fake_id": {"fake_mention_id": 1}},
                         f"Insult count map has unexpected details! {insult_manager.insult_count_map}")
