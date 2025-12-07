# DanceDB

A comprehensive dance database management system with Spotify integration and Copperknob import functionality.

## Features

- **Dance Management**: Organize and manage line dance information
- **Spotify Integration**: Search for songs, view details, and link tracks to dances
- **Copperknob Import**: Automatically extract dance information from Copperknob step sheets
- **PDF Management**: Download and organize dance step sheets
- **BPM Detection**: Automatic tempo detection for songs

## Quick Start

1. **Install dependencies**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Set up Spotify credentials** (optional):
   ```bash
   export SPOTIFY_CLIENT_ID="your_client_id"
   export SPOTIFY_CLIENT_SECRET="your_client_secret"
   ```

3. **Run the Dance Manager GUI**:
   ```bash
   python run_dance_gui.py
   ```

4. **Run the Copperknob Import GUI**:
   ```bash
   python run_copperknob_gui.py
   ```

## Project Structure

```
DanceDB/
├── src/                          # Source code
│   ├── dance.py                  # Dance model
│   ├── song.py                   # Song model with Spotify integration
│   ├── csv_writer.py             # CSV database handler
│   ├── dance_gui.py              # Main dance management GUI
│   ├── copperknob_import_gui.py  # Copperknob import GUI
│   ├── copperknob_scraper.py     # Web scraping logic
│   └── myspotipy/                # Spotify API wrapper
├── tests/                        # Test files
│   ├── unit/                     # Unit tests
│   └── debug/                    # Debug scripts
├── scripts/                      # Utility scripts
├── docs/                         # Documentation
├── pdfs/                         # Downloaded step sheets
├── run_dance_gui.py              # Launcher for dance GUI
├── run_copperknob_gui.py         # Launcher for Copperknob GUI
└── requirements.txt              # Python dependencies
```

## Usage

### Dance Manager GUI

The main GUI for managing your dance database:
- View and edit dance information
- Search and add songs from Spotify
- Manage multiple songs per dance
- View album artwork and track details

### Copperknob Import GUI

Import dance information from Copperknob:
1. Paste a Copperknob URL
2. Automatically extracts dance details
3. Download PDF step sheets
4. Save to your dance database

## Dependencies

- Python 3.8+
- tkinter (GUI)
- requests (HTTP)
- beautifulsoup4 (Web scraping)
- selenium (PDF downloads)
- Pillow (Image handling)

See `requirements.txt` for complete list.

## Configuration

Spotify credentials are stored in `~/.myspotipy/config.json` after first login.

For more details, see the [Setup Guide](docs/SETUP_GUIDE.md).

## License

Private project for personal use.
