from sqlite_database import SQLiteDatabase

# Create a test record
test_record = {
    'name': 'Test Dance',
    'aka': 'Testy',
    'level': 'Beginner',
    'choreographers': '[{"name": "Jane Doe", "location": "USA"}]',
    'release_date': '2025-12-08',
    'notes': 'Test note',
    'copperknob_id': '12345',
    'priority': 'High',
    'known': 'Yes',
    'category': 'Line',
    'other_info': 'Learn, Practice',
    'frequency': 'Weekly',
    'songs': '[{"name": "Test Song", "artist": "Test Artist"}]'
}

db = SQLiteDatabase()
db.add_record(test_record)
print('Test record inserted successfully.')
