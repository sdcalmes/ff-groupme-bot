import gspread
from models.Sidebet import Sidebet
import datetime

class Sheets:

    def __init__(self, sheet_id: str, starting_worksheet=""):
        self.gc = gspread.service_account(filename='resources/lathropolis-google-credentials.json')
        self.sheet = self.gc.open_by_key(sheet_id)
        self.worksheet = self.sheet.worksheet(starting_worksheet)

    def set_worksheet_name(self, workseet_name):
        self.worksheet = self.sheet.worksheet(workseet_name)


    def add_sidebet(self, sidebet: Sidebet):
        datas = [str(datetime.datetime.now()), sidebet.owner_a, sidebet.owner_b, sidebet.consequence, sidebet.details]
        self.worksheet.append_row(datas, table_range="A1:E1", value_input_option='USER_ENTERED')
