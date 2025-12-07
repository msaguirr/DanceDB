# Project Organization Summary

## Changes Made (December 6, 2025)

### New Directory Structure

The DanceDB project has been reorganized into a clean, professional structure:

```
DanceDB/
├── src/                          # All source code
│   ├── dance.py                  # Dance model
│   ├── song.py                   # Song model with Spotify integration
│   ├── csv_writer.py             # CSV database handler
│   ├── dance_gui.py              # Main dance management GUI
│   ├── copperknob_import_gui.py  # Copperknob import GUI
│   ├── copperknob_scraper.py     # Web scraping logic
│   └── myspotipy/                # Custom Spotify API wrapper
│       ├── __init__.py
│       ├── auth.py
│       ├── client.py
│       ├── exceptions.py
│       └── oauth.py
├── tests/                        # All test files
│   ├── unit/                     # Unit tests
│   │   ├── test_audio_features.py
│   │   ├── test_bpm.py
│   │   ├── test_browser_open.py
│   │   ├── test_client.py
│   │   └── test_song_scraper.py
│   └── debug/                    # Debug/diagnostic scripts
│       ├── debug_copperknob.py
│       └── diagnose_spotify.py
├── scripts/                      # Utility scripts
│   ├── old_gui.py               # Legacy GUI (archived)
│   └── run_gui.sh               # Legacy launch script (updated)
├── docs/                         # Documentation
│   ├── CHANGELOG.md             # Change history
│   ├── FIX_SUMMARY.py           # Technical notes on fixes
│   ├── SETUP_GUIDE.md           # Setup instructions
│   └── examples/                # Example code
│       └── quickstart.py
├── pdfs/                         # Downloaded Copperknob step sheets
├── .gitignore                    # Git ignore rules
├── README.md                     # Main project documentation
├── requirements.txt              # Python dependencies
├── run_dance_gui.py             # Launcher for Dance Manager GUI
└── run_copperknob_gui.py        # Launcher for Copperknob Import GUI
```

### Files Moved

**Source Code** → `src/`
- `dance.py`, `song.py`, `csv_writer.py`
- `dance_gui.py`, `copperknob_import_gui.py`, `copperknob_scraper.py`
- `myspotipy/` (entire directory)

**Tests** → `tests/unit/`
- `test_audio_features.py`, `test_bpm.py`, `test_browser_open.py`
- `test_song_scraper.py`, `test_client.py`

**Debug Scripts** → `tests/debug/`
- `debug_copperknob.py`, `diagnose_spotify.py`

**Documentation** → `docs/`
- `CHANGELOG.md`, `FIX_SUMMARY.py`, `SETUP_GUIDE.md`
- `examples/` directory

**Utility Scripts** → `scripts/`
- `run_gui.sh` (updated to use new structure)
- `gui.py` → renamed to `old_gui.py` (archived)

### Files Removed

- `:memory:` - Empty CSV template file (no longer needed)
- `__pycache__/` directories - Python cache (cleaned up)

### New Files Created

**Launcher Scripts:**
- `run_dance_gui.py` - Main application launcher
- `run_copperknob_gui.py` - Copperknob import tool launcher

**Configuration:**
- `.gitignore` - Git ignore rules for Python projects

**Documentation:**
- `README.md` - Updated with new structure and usage instructions

### How to Use

#### Running the Applications

**Dance Manager GUI:**
```bash
python run_dance_gui.py
```

**Copperknob Import GUI:**
```bash
python run_copperknob_gui.py
```

Both launchers automatically add the `src/` directory to Python's path, so imports work correctly.

#### For Development

All source files are now in `src/`, making it easy to:
- Import modules: `from dance import Dance`
- Run tests: `pytest tests/unit/`
- Debug issues: Use scripts in `tests/debug/`

### Benefits of New Structure

1. **Clear Separation**: Source code, tests, and documentation are clearly separated
2. **Professional Layout**: Follows Python best practices for project organization
3. **Easy Navigation**: Related files are grouped together
4. **Git-Friendly**: Proper `.gitignore` excludes generated files
5. **Maintainable**: Easy to find and update specific components
6. **Scalable**: Structure supports future growth

### Backwards Compatibility

- Old `run_gui.sh` script updated to work with new structure
- All functionality preserved - just better organized
- Import paths handled automatically by launcher scripts

### Next Steps

To further improve the project, consider:
- Adding a `setup.py` or `pyproject.toml` for proper package installation
- Creating automated tests with pytest configuration
- Adding continuous integration (CI) setup
- Documenting the API with Sphinx
