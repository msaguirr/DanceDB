from db.models import get_connection, initialize_db

def insert_sample_dance():
	conn = get_connection()
	c = conn.cursor()
	c.execute('''
		INSERT INTO dances (name, choreographer, level, stepsheet_url, known_status, category, priority, action, notes)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
	''', (
		"Countdown",
		"Turn Around (5,4,3,2,1) by Flo Rida",
		"Improver",
		"Step Sheet Link",
		"No",
		None,  # category (e.g., Learn Next, Learn Soon, etc.)
		"High",
		"Learn",
		"32 count, 4 wall"
	))
	conn.commit()
	conn.close()
	print("Sample dance inserted.")

if __name__ == "__main__":
	initialize_db()
	insert_sample_dance()
