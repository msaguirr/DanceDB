# DanceDB Changelog

## Recent Updates - Enhanced Song Data Extraction

### Latest Changes (Song Page Scraping)

**Automatic Song Page Following**
- Import GUI now automatically follows song links on Copperknob step sheets
- Extracts song data from dedicated song pages instead of step sheet pages
- More reliable BPM extraction from song pages

**Spotify Integration**
- Added Spotify URL extraction from song pages
- Spotify links are automatically found and saved with song data
- Stored in song JSON: `{'name': 'Song', 'artist': 'Artist', 'bpm': 120, 'spotify_url': 'https://...'}`

**Enhanced Data Flow**
1. User enters Copperknob step sheet URL
2. System extracts dance metadata (name, level, choreographers, etc.)
3. System automatically finds and follows song link
4. Song page is scraped for: song name, artist, BPM, Spotify URL
5. All data is populated in GUI for review/editing

### Previous Updates - Choreographer & Release Date Support

### New Features

**Multiple Choreographers with Locations**
- Added support for multiple choreographers, each with their own location
- Data structure: `[{'name': 'John Doe', 'location': 'USA'}, {'name': 'Jane Smith', 'location': 'UK'}]`
- Stored as JSON in CSV database
- Display format: "John Doe (USA) & Jane Smith (UK)"

**Release Date Field**
- Added release_date field to track when dances were choreographed
- Automatically extracted from Copperknob step sheets
- Patterns supported: "Date: March 2020", "Released: 3/2020", or just "2020"

### CSV Schema Update

**New Fields:**
- `choreographers` (JSON list) - replaced single `choreographer` field
- `release_date` (string) - new field

**Complete Schema:**
```python
["name", "level", "choreographers", "release_date", "songs", "notes"]
```

### Files Modified

1. **copperknob_import_gui.py**
   - Updated choreographer extraction to parse multiple choreographers with locations
   - Format: "Name (Location) & Name2 (Location2)"
   - Added release date extraction with multiple pattern matching
   - Updated GUI to show choreographer(s) and release date fields
   - Saves choreographers as JSON array

2. **dance_gui.py**
   - Updated DEFAULT_FIELDS to include new fields
   - Enhanced Edit Dance dialog with choreographer and release_date fields
   - Parses and displays choreographers in "Name (Location)" format

3. **csv_writer.py**
   - No changes needed (fieldnames are passed dynamically)

### Usage

**Import GUI:**
1. Enter a Copperknob URL (e.g., https://www.copperknob.co.uk/stepsheets/...)
2. Click "Fetch Data from URL"
3. Choreographers and release date are automatically extracted
4. Edit if needed - use format: "Name (Location) & Name2 (Location2)"
5. Click "Save to Database"

**Main GUI:**
1. Select a dance and click "Edit Dance"
2. Edit choreographer(s) using the format: "Name (Location) & Name2 (Location2)"
3. Add or edit release date
4. Save changes

### Data Migration

Existing CSV files will automatically gain the new columns when accessed by the updated code. Old dances will have empty choreographers and release_date fields.

To update existing dances, use the Edit Dance dialog in dance_gui.py or re-import from Copperknob URLs.
