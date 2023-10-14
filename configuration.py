import os, sys
import json

CONFIG_FILE = 'resources/configs/config_dod_test.json'


class Configuration:
    REQUIRED_CONFIGS = ["GROUPME_API_TOKEN", "GROUPME_BOT_NAME", "GROUPME_BOT_ID", "GROUPME_GROUP_ID",
                        "SLEEPER_LEAGUE_ID", "GOOGLE_SHEET_ID", "WORKSHEET_NAME"]
    OTHER_CONFIGS = {
        'GROUPME_API_URL': 'https://api.groupme.com/v3/',
        'PLAYER_FILE': 'resources/players.db'
    }

    def __init__(self):
        if os.environ.get('DEBUG') == 'True':
            print(f'In debug mode! Using {CONFIG_FILE}')
            with open(CONFIG_FILE) as config_file:
                self.config = json.load(config_file)
        else:
            self.config = {}
            # Ensure we have all necessary configs
            for config_item in Configuration.REQUIRED_CONFIGS:
                try:
                    var = os.environ[config_item]
                    self.config[config_item] = var
                except KeyError:
                    print(f'[error]: {config_item} environment variable required')
                    sys.exit(1)
        self.config.update(Configuration.OTHER_CONFIGS)

    def get_all_configs(self):
        return self.config

    def get_config_field(self, field):
        if self.config.get(field):
            return self.config[field]
        else:
            return None
#
# def import_config():
#     global CONFIG
#     with open('resources/config_lathropolis.json') as config_file:
#         CONFIG = json.load(config_file)
#
#
# def write_to_config(config_entry, value):
#     with open('resources/config_lathropolis.json', 'w', encoding='utf-8') as config_file:
#         CONFIG[config_entry] = value
#         json.dump(CONFIG, config_file, ensure_ascii=False, indent=4)
