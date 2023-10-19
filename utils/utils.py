import json


class Utils:

    @staticmethod
    def pprint(string):
        print(json.dumps(string, indent=2))
