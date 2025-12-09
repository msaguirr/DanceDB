import sqlite3
import os

DEFAULT_DB = os.path.join(os.path.expanduser("~"), "dances.db")

class SQLiteDatabase:
    def __init__(self, db_path=DEFAULT_DB):
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS dances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    aka TEXT,
                    level TEXT,
                    choreographers TEXT,
                    release_date TEXT,
                    notes TEXT,
                    copperknob_id TEXT,
                    priority TEXT,
                    known TEXT,
                    category TEXT,
                    other_info TEXT,
                    frequency TEXT,
                    songs TEXT
                )
            ''')
            conn.commit()

    def add_record(self, record):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO dances (
                    name, aka, level, choreographers, release_date, notes, copperknob_id, priority, known, category, other_info, frequency, songs
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.get('name'),
                record.get('aka'),
                record.get('level'),
                record.get('choreographers'),
                record.get('release_date'),
                record.get('notes'),
                record.get('copperknob_id'),
                record.get('priority'),
                record.get('known'),
                record.get('category'),
                record.get('other_info'),
                record.get('frequency'),
                record.get('songs')
            ))
            conn.commit()

    # Optionally, add more methods for querying, updating, deleting, etc.
