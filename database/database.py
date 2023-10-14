import sqlite3
from models.Sidebet import Sidebet

class Database(object):
    """sqlite3 database class that holds testers jobs"""
    DB_LOCATION = "database/databases/"

    def __init__(self, db_name):
        """Initialize db class variables"""
        db_name = Database.DB_LOCATION + db_name
        self.connection = sqlite3.connect(db_name)
        self.cur = self.connection.cursor()

    def close(self):
        """close sqlite3 connection"""
        self.connection.close()

    def execute(self, new_data: Sidebet):
        """execute a row of data to current cursor"""
        sql = """insert into sidebets(id, owner_a, owner_b, consequence, details) VALUES (?, ?, ?, ?, ?);"""

        data_tuple = [None, new_data.owner_a, new_data.owner_b, new_data.consequence, new_data.details]
        self.cur.execute(sql, data_tuple)

    def executemany(self, many_new_data):
        """add many new data to database in one go"""
        # self.create_table()
        self.cur.executemany('REPLACE INTO jobs VALUES(?, ?, ?, ?)', many_new_data)

    def create_sidebets_table(self):
        """create a database table if it does not exist already"""
        sql = 'create table if not exists sidebets( id INTEGER PRIMARY KEY,' \
                                                           'owner_a TEXT NOT NULL,' \
                                                           'owner_b TEXT NOT NULL,' \
                                                           'consequence TEXT NOT NULL,' \
                                                           'details TEXT NOT NULL );'

        self.cur.execute(sql)


    def commit(self):
        """commit changes to database"""
        self.connection.commit()

    def list_tables(self):
        sql = ".tables"
        self.cur.execute('SELECT name FROM sqlite_master WHERE type="table";')
        results = self.cur.fetchall()
        for result in results:
            print(result[0])

    def __enter__(self):
        return self

    def __exit__(self, ext_type, exc_value, traceback):
        self.cur.close()
        if isinstance(exc_value, Exception):
            self.connection.rollback()
        else:
            self.connection.commit()
        self.connection.close()
