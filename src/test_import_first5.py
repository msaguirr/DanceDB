import csv
import sqlite3

DB_PATH = 'data/dance_db.sqlite3'
CSV_PATH = 'assets/copperknob_links_and_songs.csv'

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for i, row in enumerate(reader):
            if i >= 5:
                break
            stepsheet_url, song_title = row[0], row[1]
            # Insert or get song
            cur.execute('SELECT id FROM songs WHERE title = ?', (song_title,))
            song_row = cur.fetchone()
            if song_row:
                song_id = song_row[0]
            else:
                cur.execute('INSERT INTO songs (title) VALUES (?)', (song_title,))
                song_id = cur.lastrowid
            # Insert or get dance
            cur.execute('SELECT id FROM dances WHERE stepsheet_url = ?', (stepsheet_url,))
            dance_row = cur.fetchone()
            if dance_row:
                dance_id = dance_row[0]
            else:
                cur.execute('INSERT INTO dances (name, stepsheet_url) VALUES (?, ?)', (song_title, stepsheet_url))
                dance_id = cur.lastrowid
            # Link dance and song
            cur.execute('SELECT id FROM dance_songs WHERE dance_id = ? AND song_id = ?', (dance_id, song_id))
            link_row = cur.fetchone()
            if not link_row:
                cur.execute('INSERT INTO dance_songs (dance_id, song_id) VALUES (?, ?)', (dance_id, song_id))
            print(f"Imported dance: stepsheet_url={stepsheet_url}, song={song_title}")
    conn.commit()
    conn.close()

if __name__ == '__main__':
    main()
