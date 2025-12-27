# DanceDB database schema for dances and songs
# This schema supports dances with and without CopperKnob links

-- Song table
CREATE TABLE IF NOT EXISTS Song (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
    -- Add other song fields as needed
);

-- Dance table
CREATE TABLE IF NOT EXISTS Dance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    copperknob_id INTEGER UNIQUE, -- nullable, unique if present
    stepsheet_link TEXT,          -- nullable for non-CopperKnob dances
    name TEXT,                    -- optional dance name
    song_id INTEGER,              -- foreign key to Song
    source TEXT,                  -- e.g., 'copperknob', 'manual', etc.
    -- Add other dance fields as needed
    FOREIGN KEY (song_id) REFERENCES Song(id)
);
