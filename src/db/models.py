import sqlite3

DB_PATH = "dance_db.sqlite3"

def get_connection():
	return sqlite3.connect(DB_PATH)

def initialize_db():
	conn = get_connection()
	c = conn.cursor()
	# Dances table
	c.execute('''
		CREATE TABLE IF NOT EXISTS dances (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			name TEXT NOT NULL,
			choreographer TEXT,
			release_date TEXT,
			level TEXT,
			count TEXT,
			wall TEXT,
			tag TEXT,
			restart TEXT,
			stepsheet_url TEXT,
			known_status TEXT,
			category TEXT,
			priority TEXT,
			action TEXT,
			notes TEXT
		)
	''')
	# Songs table
	c.execute('''
		CREATE TABLE IF NOT EXISTS songs (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			title TEXT NOT NULL,
			bpm INTEGER,
			genre TEXT,
			spotify_url TEXT,
			notes TEXT
		)
	''')
	# Dance-Song join table
	c.execute('''
		CREATE TABLE IF NOT EXISTS dance_songs (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			dance_id INTEGER,
			song_id INTEGER,
			FOREIGN KEY(dance_id) REFERENCES dances(id),
			FOREIGN KEY(song_id) REFERENCES songs(id)
		)
	''')
	# Song artists
	c.execute('''
		CREATE TABLE IF NOT EXISTS song_artists (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			song_id INTEGER,
			artist_name TEXT,
			FOREIGN KEY(song_id) REFERENCES songs(id)
		)
	''')
	# Song tags
	c.execute('''
		CREATE TABLE IF NOT EXISTS song_tags (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			song_id INTEGER,
			tag TEXT,
			FOREIGN KEY(song_id) REFERENCES songs(id)
		)
	''')
	# Song sources
	c.execute('''
		CREATE TABLE IF NOT EXISTS song_sources (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			song_id INTEGER,
			source_id INTEGER,
			FOREIGN KEY(song_id) REFERENCES songs(id),
			FOREIGN KEY(source_id) REFERENCES sources(id)
		)
	''')
	# Sources
	c.execute('''
		CREATE TABLE IF NOT EXISTS sources (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			name TEXT,
			url TEXT,
			type TEXT
		)
	''')
	conn.commit()
	conn.close()

if __name__ == "__main__":
	initialize_db()
	print("Database initialized.")
