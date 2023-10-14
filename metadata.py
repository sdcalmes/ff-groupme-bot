import os
import pickle

METADATA_FILE = 'resources/metadata.json'

class Metadata:

    def __init__(self):
        self.data: dict[str, str] = {}
        if os.path.isfile(METADATA_FILE):
            with open(METADATA_FILE, 'rb') as f:
                self.data = pickle.load(f)
        else:
            with open(METADATA_FILE, 'wb') as f:
                pickle.dump(self.data, f)

    def get_metadata_field(self, field):
        if self.data.get(field):
            return self.data[field]
        else:
            self.data[field] = 0
            return 0

    def get_current_metadata(self):
        return self.data

    def write_metadata_field(self, field, data):
        self.data[field] = data
        self.__write_metadata_file()

    def __write_metadata_file(self):
        with open(METADATA_FILE, 'wb') as f:
            pickle.dump(self.data, f)
