from .models import get_connection

def get_songs_for_dance(dance_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT s.title
        FROM songs s
        JOIN dance_songs ds ON ds.song_id = s.id
        WHERE ds.dance_id = ?
    ''', (dance_id,))
    songs = [row[0] for row in c.fetchall()]
    conn.close()
    return songs

def get_dance_id_by_name_and_choreo(name, choreographer):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id FROM dances WHERE name=? AND choreographer=?', (name, choreographer))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None
