#!/usr/bin/env python3
"""GUI for importing dance data from Copperknob step sheets.

This tool allows you to paste a Copperknob URL and automatically extract:
- Dance name
- Choreographer
- Level/difficulty
- Count, walls, tags, restarts
- Song name, artist, and BPM (by following the song link)
"""
import re
import re
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
from bs4 import BeautifulSoup
import re
from typing import Optional, Dict
import json
import os
import tempfile
import time
from csv_writer import CSVDatabase

DEFAULT_CSV = os.path.join(os.path.expanduser("~"), "dances.csv")

import re
DEFAULT_FIELDS = ["name", "aka", "level", "choreographers", "release_date", "songs", "notes", "copperknob_id", "priority", "known", "category", "other_info", "frequency"]


class CopperknobImporter:
    """Scrape dance and song data from Copperknob step sheets."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def extract_dance_data(self, url: str) -> Optional[Dict]:
        """Extract dance information from a Copperknob step sheet URL.
        
        Args:
            url: URL to a Copperknob step sheet page
            
        Returns:
            Dictionary with dance metadata, or None if extraction fails
        """
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            data = {
                'url': url,
                'dance_name': None,
                'aka': '',
                'choreographers': [],  # List of dicts: [{'name': 'John Doe', 'location': 'USA'}, ...]
                'release_date': None,
                'level': None,
                'count': None,
                'walls': None,
                'tags': None,
                'restarts': None,
                'songs': [],  # List of song dicts with all fields
                'notes': ''
            }
            # Extract AKA (alternate name) from the dance name if present
            # e.g., "Saddle Up Shawty aka Hip Hop Twist"
            if data['dance_name']:
                aka_match = re.search(r'\baka\s+(.+)$', data['dance_name'], re.I)
                if aka_match:
                    aka = aka_match.group(1).strip()
                    # Remove "aka ..." from dance_name
                    data['aka'] = aka
                    data['dance_name'] = re.sub(r'\s*aka\s+.+$', '', data['dance_name'], flags=re.I).strip()
            
            # Get page text for pattern matching
            page_text = soup.get_text()
            
            # Extract dance name - it's displayed prominently on the page
            # Try multiple methods to find it
            
            # Method 1: Look for the first h1 tag (usually the dance name on Copperknob)
            h1_tag = soup.find('h1')
            if h1_tag:
                potential_name = h1_tag.get_text(strip=True)
                # Make sure it's not a generic page title
                if potential_name and 'stepsheet' not in potential_name.lower() and 'copperknob' not in potential_name.lower():
                    data['dance_name'] = potential_name
                    print(f"DEBUG: Found dance name in h1: {data['dance_name']}")
            
            # Method 2: Look for the dance name from URL as last resort
            if not data['dance_name']:
                # Extract from URL: /stepsheets/109973/more-dessert -> "More Dessert"
                import re
                url_match = re.search(r'/stepsheets/\d+/([^/?]+)', url)
                if url_match:
                    url_name = url_match.group(1).replace('-', ' ').title()
                    data['dance_name'] = url_name
                    print(f"DEBUG: Extracted dance name from URL: {data['dance_name']}")
            
            # Look for structured data sections - Copperknob typically has labeled fields
            
            # Extract choreographer(s) with location(s) and release date
            # The format on Copperknob is: "Choreographer: Name (Location) & Name2 (Location2) - Date"
            # Look for "Choreographer:" label and get the next line
            choreo_text = None
            lines = page_text.split('\n')
            for i, line in enumerate(lines):
                if re.match(r'^\s*Choreographer:\s*$', line, re.I):
                    # Get next non-empty line
                    for j in range(i+1, min(i+5, len(lines))):
                        val = lines[j].strip()
                        if val:
                            choreo_text = val
                            break
                    break
            
            if choreo_text:
                # Check if date is at the end: "Name (Location) & Name2 (Location2) - March 2016"
                date_match = re.search(r'\s+-\s+((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}|\d{1,2}/\d{4}|\d{4})$', choreo_text, re.I)
                if date_match:
                    data['release_date'] = date_match.group(1).strip()
                    # Remove the date from choreo_text
                    choreo_text = re.sub(r'\s+-\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}$', '', choreo_text, flags=re.I)
                    choreo_text = re.sub(r'\s+-\s+\d{1,2}/\d{4}$', '', choreo_text)
                    choreo_text = re.sub(r'\s+-\s+\d{4}$', '', choreo_text)
                
                # Parse multiple choreographers separated by &, 'and', or commas
                choreo_parts = re.split(r'\s*(?:,\s*(?:and\s+)?|&\s*|(?:\s+and\s+))\s*', choreo_text)
                choreo_parts = [p.strip() for p in choreo_parts if p.strip()]
                for part in choreo_parts:
                    # Extract name and location: "John Doe (USA, UK)" or "John Doe"
                    match = re.match(r'([^(]+)(?:\(([^)]+)\))?', part.strip())
                    if match:
                        name = match.group(1).strip()
                        location = match.group(2).strip() if match.group(2) else ''
                        data['choreographers'].append({
                            'name': name,
                            'location': location
                        })
            
            # If release date wasn't found in choreographer line, try other patterns
            if not data['release_date']:
                date_patterns = [
                    r'(?:Date|Released|Choreographed)[:\s]+([^\n\r]+?)(?=\s*\n|\s*$|Choreographer|Level)',
                    r'\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b',
                    r'\b(\d{1,2}/\d{4})\b',
                ]
                for pattern in date_patterns:
                    date_match = re.search(pattern, page_text, re.I)
                    if date_match:
                        data['release_date'] = date_match.group(1).strip()
                        break
            
            # Extract level/difficulty - try multiple approaches
            # 1. Look for "Level:" or "Difficulty:" label
            level_match = re.search(r'(?:Level|Difficulty)[:\s]+([^\n\r]+?)(?=\s*\n|\s*$|Choreographer|Count|Wall)', page_text, re.I)
            if level_match:
                level_text = level_match.group(1).strip()
                # Clean up common level formats
                level_text = re.sub(r'\s*-\s*.*$', '', level_text)  # Remove anything after dash
                level_text = re.sub(r'\s*\(.*?\)', '', level_text)  # Remove parenthetical
                data['level'] = level_text
            else:
                # 2. Try finding it in a structured element
                level_elem = soup.find(string=re.compile(r'Level|Difficulty', re.I))
                if level_elem:
                    parent = level_elem.parent
                    if parent:
                        next_elem = parent.find_next_sibling()
                        if next_elem:
                            data['level'] = next_elem.get_text(strip=True)
                        else:
                            text = parent.get_text()
                            match = re.search(r'(?:Level|Difficulty)[:\s]+([^\n\r]+)', text, re.I)
                            if match:
                                data['level'] = match.group(1).strip()
            
            # Extract count, walls, tags, restarts
            # Copperknob has labels on one line and values on the next line
            page_text = soup.get_text()
            lines = page_text.split('\n')
            
            # Count - look for "Count:" label and get next non-empty line
            for i, line in enumerate(lines):
                if re.match(r'^\s*Count:\s*$', line, re.I):
                    # Get next non-empty line
                    for j in range(i+1, min(i+5, len(lines))):
                        val = lines[j].strip()
                        if val and val.isdigit():
                            data['count'] = int(val)
                            break
                    break
            
            # Walls - look for "Wall:" label and get next non-empty line
            for i, line in enumerate(lines):
                if re.match(r'^\s*Wall:\s*$', line, re.I):
                    # Get next non-empty line
                    for j in range(i+1, min(i+5, len(lines))):
                        val = lines[j].strip()
                        if val and (val.isdigit() or val == '-'):
                            if val.isdigit():
                                data['walls'] = int(val)
                            break
                    break
            
            # Tags - search entire page text for tag mentions
            # Common patterns:
            # - "Tag: after wall 3" or "Tags: after walls 2 and 4"
            # - "There is a tag after wall 3"
            # - "Tag after 16 counts on wall 3"
            # - "Tag 1: 2 counts", "Tag 2: 4 counts" (multiple numbered tags)
            tag_count = 0
            tag_numbers_seen = set()
            
            for line in lines:
                line_lower = line.lower()
                # Look for lines mentioning "tag" (but not "vintage", "footage", etc.)
                if re.search(r'\btags?\b', line_lower) and not re.search(r'vintage|footage|hashtag', line_lower):
                    # Pattern 1: Numbered tags like "Tag 1:", "Tag 2:", etc.
                    numbered_tag = re.search(r'\btag\s+(\d+)\b', line, re.I)
                    if numbered_tag:
                        tag_numbers_seen.add(int(numbered_tag.group(1)))
                    
                    # Pattern 2: Count wall numbers mentioned in tag-related lines
                    # Common: "tag after wall 3", "tags after walls 2 and 4"
                    wall_matches = re.findall(r'wall\s+(\d+)', line, re.I)
                    if wall_matches:
                        tag_count = max(tag_count, len(wall_matches))
                    
                    # Pattern 3: Explicit number: "2 tags", "1 tag"
                    num_match = re.search(r'(\d+)\s+tags?\b', line, re.I)
                    if num_match:
                        tag_count = max(tag_count, int(num_match.group(1)))
            
            # If we found numbered tags (Tag 1, Tag 2), use the highest number
            if tag_numbers_seen:
                tag_count = max(tag_count, max(tag_numbers_seen))
            
            if tag_count > 0:
                data['tags'] = tag_count
            
            # Restarts - search entire page text for restart mentions
            # Common patterns:
            # - "Restart after wall 3" or "Restarts after walls 3 and 5"
            # - "Restart happens here after walls 3 and 5"
            # - "2 restarts", "There are 2 restarts"
            restart_count = 0
            for line in lines:
                line_lower = line.lower()
                if 'restart' in line_lower:
                    # Count wall numbers mentioned in restart-related lines
                    wall_matches = re.findall(r'wall\s+(\d+)', line, re.I)
                    if wall_matches:
                        restart_count = max(restart_count, len(wall_matches))
                    # Also check for explicit number: "2 restarts", "1 restart"
                    num_match = re.search(r'(\d+)\s+restarts?\b', line, re.I)
                    if num_match:
                        restart_count = max(restart_count, int(num_match.group(1)))
            if restart_count > 0:
                data['restarts'] = restart_count
            
            # Extract ALL songs from "Music:" sections (there can be multiple)
            # Format: Line with "Music:" or "Alternative Music:" followed by line with "Song Name - Artist Name"
            music_sections = []
            
            for i, line in enumerate(lines):
                # Look for "Music:", "Alternative Music:", "or:", "Also:" sections
                line_stripped = line.strip()
                is_music_section = (
                    re.match(r'^(Alternative\s+)?Music:\s*$', line_stripped, re.I) or
                    re.match(r'^(or|also):\s*$', line_stripped, re.I)
                )
                
                if is_music_section:
                    # Get next non-empty line
                    for j in range(i+1, min(i+5, len(lines))):
                        music_text = lines[j].strip()
                        if music_text:
                            song_info = {
                                'song_name': None,
                                'artist': None,
                                'artist_display': None,  # Original format for listbox display
                                'music_line_index': i
                            }
                            
                            # Parse "Song Name - Artist Name" format
                            if ' - ' in music_text:
                                parts = music_text.split(' - ', 1)
                                if len(parts) == 2:
                                    song_info['song_name'] = parts[0].strip()
                                    artist_original = parts[1].strip()
                                    # Remove duration if present like "(2:41)"
                                    artist_original = re.sub(r'\s*:\s*\([^)]+\)\s*$', '', artist_original)
                                    
                                    # Store original format for listbox display
                                    song_info['artist_display'] = artist_original
                                    
                                    # Convert & to comma separator for artist field only
                                    song_info['artist'] = artist_original.replace(' & ', ', ')
                                    
                                    # Extract featured artists from song title and add to artist list
                                    # Look for patterns like "feat. Artist" or "(feat. Artist)" or "ft. Artist"
                                    featured_match = re.search(r'\((?:feat\.|featuring|ft\.)\s+([^)]+)\)', song_info['song_name'], re.I)
                                    if featured_match:
                                        featured_artist = featured_match.group(1).strip()
                                        # Add featured artist to the artist field (using comma separator)
                                        song_info['artist'] = f"{song_info['artist']}, {featured_artist}"
                                        song_info['artist_display'] = f"{song_info['artist_display']} & {featured_artist}"
                                    
                                    print(f"DEBUG: Extracted song - Song: {song_info['song_name']}, Artist: {song_info['artist']}")
                            elif ' by ' in music_text.lower():
                                # Fallback: "Song by Artist" format
                                parts = re.split(r'\s+by\s+', music_text, maxsplit=1, flags=re.I)
                                if len(parts) == 2:
                                    song_info['song_name'] = parts[0].strip()
                                    song_info['artist'] = parts[1].strip()
                                    print(f"DEBUG: Extracted song (by format) - Song: {song_info['song_name']}, Artist: {song_info['artist']}")
                            else:
                                # No delimiter, just song name
                                song_info['song_name'] = music_text
                                print(f"DEBUG: Extracted song name only: {song_info['song_name']}")
                            
                            if song_info['song_name']:
                                music_sections.append(song_info)
                            break
            
            # For each song, try to find its music page link and extract details
            for song_info in music_sections:
                song_link = None
                
                # Look for song link - find any link with /music/ in the href that matches this song
                for elem in soup.find_all('a', href=True):
                    href = elem.get('href')
                    if '/music/' in href.lower():
                        link_text = elem.get_text(strip=True)
                        # Check if link text matches or is part of our song name
                        if link_text and song_info['song_name'] and (
                            link_text.lower() == song_info['song_name'].lower() or
                            link_text.lower() in song_info['song_name'].lower() or
                            song_info['song_name'].lower() in link_text.lower()
                        ):
                            song_link = href
                            print(f"DEBUG: Found song link for '{song_info['song_name']}': {song_link}")
                            break
                
                # Create song data dict with name and artist
                song_data = {
                    'song_name': song_info['song_name'],
                    'artist': song_info['artist'],
                    'artist_display': song_info.get('artist_display', song_info['artist']),  # Use original format for display
                    'genre': None,
                    'bpm': None,
                    'spotify_url': None,
                    'album_cover': None,
                    'release_date': None,
                    'duration': None
                }
                
                # If we found a song link, follow it to get additional details
                if song_link:
                    if not song_link.startswith('http'):
                        song_link = 'https://www.copperknob.co.uk' + song_link
                    print(f"DEBUG: Following song link for '{song_info['song_name']}'")
                    extra_data = self.extract_song_data(song_link)
                    if extra_data:
                        # Update with additional song data, filtering out "-" placeholders
                        genre = extra_data.get('genre')
                        if genre and genre != '-':
                            song_data['genre'] = genre
                        if extra_data.get('bpm'):
                            song_data['bpm'] = extra_data['bpm']
                        if extra_data.get('spotify_url'):
                            song_data['spotify_url'] = extra_data['spotify_url']
                        if extra_data.get('album_cover'):
                            song_data['album_cover'] = extra_data['album_cover']
                        release_date = extra_data.get('release_date')
                        if release_date and release_date != '-':
                            song_data['release_date'] = release_date
                        duration = extra_data.get('duration')
                        if duration and duration != '-':
                            song_data['duration'] = duration
                        print(f"DEBUG: Updated '{song_info['song_name']}' with data - genre={song_data.get('genre')}, bpm={song_data.get('bpm')}")
                
                # Add this song to the list
                data['songs'].append(song_data)
            
            
            return data
            
        except Exception as e:
            print(f"Error extracting dance data: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def extract_song_data(self, url: str) -> Optional[Dict]:
        """Extract song information from a Copperknob song page.
        
        Args:
            url: URL to a Copperknob song page
            
        Returns:
            Dictionary with song_name, artist, bpm, song_url
        """
        try:
            print(f"DEBUG extract_song_data: Fetching {url}")
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            data = {
                'song_url': url,
                'genre': None,
                'bpm': None,
                'spotify_url': None,
                'release_date': None,
                'duration': None,
                'album_cover': None
            }
            
            # Get text lines for parsing
            page_text = soup.get_text()
            lines = page_text.split('\n')
            
            # Extract structured data - Copperknob format: "Field:Value" on same line
            for line in lines:
                line_stripped = line.strip()
                
                # Genre: "Genre:Pop"
                if line_stripped.startswith('Genre:'):
                    data['genre'] = line_stripped.replace('Genre:', '').strip()
                    print(f"DEBUG: Found genre: {data['genre']}")
                
                # BPM: "BPM:97"
                elif line_stripped.startswith('BPM:'):
                    bpm_text = line_stripped.replace('BPM:', '').strip()
                    bpm_match = re.search(r'(\d+)', bpm_text)
                    if bpm_match:
                        data['bpm'] = int(bpm_match.group(1))
                        print(f"DEBUG: Found BPM: {data['bpm']}")
                
                # Release date: "Released:25 September 2015"
                elif line_stripped.startswith('Released:'):
                    data['release_date'] = line_stripped.replace('Released:', '').strip()
                    print(f"DEBUG: Found release date: {data['release_date']}")
                
                # Duration: "Duration:3m 31s"
                elif line_stripped.startswith('Duration:'):
                    data['duration'] = line_stripped.replace('Duration:', '').strip()
                    print(f"DEBUG: Found duration: {data['duration']}")
            
            
            # Extract album cover image
            # Look for image with alt text containing artist/song or with music service URLs
            for img in soup.find_all('img'):
                src = img.get('src', '')
                alt = img.get('alt', '')
                # Album cover is typically from music services (Apple Music, etc.)
                if src and ('mzstatic.com' in src or 'spotify' in src or 'album' in src.lower()):
                    # Make sure it's not an icon/logo
                    if not any(icon in src.lower() for icon in ['svg', 'logo', 'icon', 'button']):
                        data['album_cover'] = src
                        print(f"DEBUG: Found album cover: {src}")
                        break
            
            if not data['album_cover']:
                print(f"DEBUG: No album cover found")
            
            # Extract Spotify link
            spotify_link = soup.find('a', href=re.compile(r'spotify\.com', re.I))
            if spotify_link:
                data['spotify_url'] = spotify_link.get('href')
                print(f"DEBUG: Found Spotify link: {data['spotify_url']}")
            else:
                # Try finding in text/script
                spotify_match = re.search(r'https?://(?:open\.)?spotify\.com/[^\s\'"<>]+', resp.text)
                if spotify_match:
                    data['spotify_url'] = spotify_match.group(0)
                    print(f"DEBUG: Found Spotify link in text: {data['spotify_url']}")
                else:
                    print(f"DEBUG: No Spotify link found")
            
            return data
            
        except Exception as e:
            print(f"Error extracting song data: {e}")
            return None


class CopperknobImportGUI(tk.Tk):
    """GUI for importing dances from Copperknob."""
    
    def __init__(self):
        super().__init__()
        self.title("Import from Copperknob")
        self.geometry("1150x750")

        # Remove blue focus ring from all Comboboxes
        style = ttk.Style(self)
        style.map('TCombobox',
            focuscolor=[('!focus', 'white'), ('focus', 'white')],
            highlightbackground=[('active', 'white'), ('focus', 'white'), ('!focus', 'white')],
            highlightcolor=[('active', 'white'), ('focus', 'white'), ('!focus', 'white')],
            bordercolor=[('active', 'white'), ('focus', 'white'), ('!focus', 'white')],
        )
        style.configure('TCombobox', highlightthickness=0, borderwidth=0, relief='flat',
                        highlightbackground='white', highlightcolor='white', bordercolor='white')

        self.importer = CopperknobImporter()
        self.db = CSVDatabase(DEFAULT_CSV, DEFAULT_FIELDS)
        self.extracted_data = None
        # Hidden AKA field
        self.aka_var = tk.StringVar()

        self._build_ui()
    
    def _build_ui(self):
        main = ttk.Frame(self, padding=15)
        main.pack(fill=tk.BOTH, expand=True)
        
        # URL input section
        url_frame = ttk.LabelFrame(main, text="Step 1: Enter Copperknob URL", padding=10)
        url_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(url_frame, text="Paste the URL to a Copperknob step sheet:").pack(anchor=tk.W, pady=(0, 5))
        
        url_input_frame = ttk.Frame(url_frame)
        url_input_frame.pack(fill=tk.X)
        
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_input_frame, textvariable=self.url_var, width=60)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.url_entry.bind('<Return>', lambda e: self._fetch_data())
        
        self.fetch_btn = ttk.Button(url_input_frame, text="Fetch Data", command=self._fetch_data)
        self.fetch_btn.pack(side=tk.LEFT)
        
        # Extracted data display section
        data_frame = ttk.LabelFrame(main, text="Step 2: Review Extracted Data", padding=10)
        data_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        

        # Create a grid for the extracted data
        row = 0
        
        # Dance name row - use grid for all widgets for fixed, independent positions
        dance_row = ttk.Frame(data_frame)
        dance_row.grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=3)
        # Label
        ttk.Label(dance_row, text="Dance Name:", width=13).grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        # Dedicated frame for dance name input (Entry/Combobox)
        self.dance_name_var = tk.StringVar()
        # Fixed pixel width for dance name input frame (matches Entry width=45 and Combobox width=43)
        DANCE_NAME_INPUT_WIDTH = 340  # px, adjust as needed for your font/UI
        self.dance_name_input_frame = ttk.Frame(dance_row, width=DANCE_NAME_INPUT_WIDTH)
        self.dance_name_input_frame.grid(row=0, column=1, sticky="nsew")
        self.dance_name_input_frame.grid_propagate(False)  # Prevent frame from resizing to contents
        self.dance_name_input_frame.grid_columnconfigure(0, minsize=DANCE_NAME_INPUT_WIDTH, weight=1)
        self.dance_name_entry = ttk.Entry(self.dance_name_input_frame, textvariable=self.dance_name_var, width=43)
        self.dance_name_entry.grid(row=0, column=0, sticky="nsew")
        # Count label and entry
        ttk.Label(dance_row, text="Count:", width=7, anchor=tk.E).grid(row=0, column=2, padx=(10, 3), sticky=tk.E)
        self.count_var = tk.StringVar()
        ttk.Entry(dance_row, textvariable=self.count_var, width=10).grid(row=0, column=3, sticky=tk.W)
        # Priority label and combobox
        ttk.Label(dance_row, text="Priority:", width=8, anchor=tk.E).grid(row=0, column=4, padx=(0, 3), sticky=tk.E)
        self.priority_var = tk.StringVar()
        self.priority_combo = ttk.Combobox(dance_row, textvariable=self.priority_var, width=12, values=[
            "", "Highest", "High", "Medium", "Low", "Lowest", "Never"
        ], state='readonly', takefocus=0)
        self.priority_combo.grid(row=0, column=5, sticky=tk.W)
        self._setup_combobox_behavior(self.priority_combo, self.priority_var)
        # Configure grid weights for fixed layout
        for i in range(6):
            dance_row.grid_columnconfigure(i, weight=0)
        row += 1
        
        # Choreographer(s) row - align with dance name row columns
        choreo_row = ttk.Frame(data_frame)
        choreo_row.grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=3)
        ttk.Label(choreo_row, text="Choreographer(s):", width=13).grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        self.choreographer_var = tk.StringVar()
        # Match dance name input frame width and grid
        choreo_input_frame = ttk.Frame(choreo_row, width=340)
        choreo_input_frame.grid(row=0, column=1, sticky="nsew")
        choreo_input_frame.grid_propagate(False)
        choreo_input_frame.grid_columnconfigure(0, minsize=340, weight=1)
        ttk.Entry(choreo_input_frame, textvariable=self.choreographer_var, width=43).grid(row=0, column=0, sticky="nsew")
        ttk.Label(choreo_row, text="Wall:", width=7, anchor=tk.E).grid(row=0, column=2, padx=(10, 3), sticky=tk.E)
        self.walls_var = tk.StringVar()
        ttk.Entry(choreo_row, textvariable=self.walls_var, width=10).grid(row=0, column=3, sticky=tk.W)
        ttk.Label(choreo_row, text="Known?:", width=8, anchor=tk.E).grid(row=0, column=4, padx=(0, 3), sticky=tk.E)
        self.known_var = tk.StringVar()
        self.known_combo = ttk.Combobox(choreo_row, textvariable=self.known_var, width=12, values=[
            "", "Yes", "No", "Partially", "On the floor"
        ], state='readonly', takefocus=0)
        self.known_combo.grid(row=0, column=5, sticky=tk.W)
        self._setup_combobox_behavior(self.known_combo, self.known_var)
        for i in range(6):
            choreo_row.grid_columnconfigure(i, weight=0)
        row += 1
        
        # Release Date row - align with dance name row columns
        release_row = ttk.Frame(data_frame)
        release_row.grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=3)
        ttk.Label(release_row, text="Release Date:", width=13).grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        self.release_date_var = tk.StringVar()
        release_input_frame = ttk.Frame(release_row, width=340)
        release_input_frame.grid(row=0, column=1, sticky="nsew")
        release_input_frame.grid_propagate(False)
        release_input_frame.grid_columnconfigure(0, minsize=340, weight=1)
        ttk.Entry(release_input_frame, textvariable=self.release_date_var, width=43).grid(row=0, column=0, sticky="nsew")
        ttk.Label(release_row, text="Tags:", width=7, anchor=tk.E).grid(row=0, column=2, padx=(10, 3), sticky=tk.E)
        self.tags_var = tk.StringVar()
        ttk.Entry(release_row, textvariable=self.tags_var, width=10).grid(row=0, column=3, sticky=tk.W)
        ttk.Label(release_row, text="Category:", width=8, anchor=tk.E).grid(row=0, column=4, padx=(0, 3), sticky=tk.E)
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(release_row, textvariable=self.category_var, width=12, values=[
            "", "Learn next", "Learn soon", "Learn later"
        ], state='readonly', takefocus=0)
        self.category_combo.grid(row=0, column=5, sticky=tk.W)
        self._setup_combobox_behavior(self.category_combo, self.category_var)
        for i in range(6):
            release_row.grid_columnconfigure(i, weight=0)
        row += 1
        
        # Level row - align with dance name row columns
        level_row = ttk.Frame(data_frame)
        level_row.grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=3)
        ttk.Label(level_row, text="Level:", width=13).grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        self.level_var = tk.StringVar()
        level_input_frame = ttk.Frame(level_row, width=340)
        level_input_frame.grid(row=0, column=1, sticky="nsew")
        level_input_frame.grid_propagate(False)
        level_input_frame.grid_columnconfigure(0, minsize=340, weight=1)
        self.level_combo = ttk.Combobox(level_input_frame, textvariable=self.level_var, width=43, values=[
            "", "Absolute Beginner", "Beginner", "Improver", "Intermediate", "Advanced"
        ], state='readonly', takefocus=0)
        self.level_combo.grid(row=0, column=0, sticky="nsew")
        self._setup_combobox_behavior(self.level_combo, self.level_var)
        ttk.Label(level_row, text="Restarts:", width=7, anchor=tk.E).grid(row=0, column=2, padx=(10, 3), sticky=tk.E)
        self.restarts_var = tk.StringVar()
        ttk.Entry(level_row, textvariable=self.restarts_var, width=10).grid(row=0, column=3, sticky=tk.W)
        ttk.Label(level_row, text="Frequency:", width=8, anchor=tk.E).grid(row=0, column=4, padx=(0, 3), sticky=tk.E)
        self.frequency_var = tk.StringVar()
        self.frequency_combo = ttk.Combobox(level_row, textvariable=self.frequency_var, width=12, values=[
            "", "Never", "Once", "Rarely", "Sometimes", "Usually", "Always"
        ], state='readonly', takefocus=0)
        self.frequency_combo.grid(row=0, column=5, sticky=tk.W)
        self._setup_combobox_behavior(self.frequency_combo, self.frequency_var)
        for i in range(6):
            level_row.grid_columnconfigure(i, weight=0)
        row += 1
        row += 1



        # Buttons and Other Info row (use grid for alignment)
        button_row = ttk.Frame(data_frame)
        button_row.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=3)

        self.stepsheet_url = ""
        self.copperknob_id = None  # Hidden field to track unique dance ID
        self.stepsheet_button = ttk.Button(button_row, text="Open in Copperknob", command=self._open_stepsheet, width=18)
        self.stepsheet_button.grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        self.stepsheet_button.config(state='disabled')

        self.pdf_url = ""
        self.pdf_path = None  # Track downloaded PDF path
        self.pdf_button = ttk.Button(button_row, text="Download PDF", command=self._download_pdf, width=12)
        self.pdf_button.grid(row=0, column=1, padx=(0, 20), sticky=tk.W)
        self.pdf_button.config(state='disabled')


        # Other Info multi-select field, aligned under 'Frequency' (column 5 in previous rows)
        # The horizontal offset should match the left edge of the 'Frequency' label above
        # The 'Frequency' label is at column=4, with a fixed width and some padding
        # Empirically, a padx of about 275 aligns with the 'Frequency' label (adjust as needed)
        other_info_row = ttk.Frame(button_row)
        other_info_row.grid(row=0, column=2, sticky=tk.W, padx=(275, 0))
        ttk.Label(other_info_row, text="Other Info:", width=8, anchor=tk.E).pack(side=tk.LEFT, padx=(0, 3))
        checkbox_frame = ttk.Frame(other_info_row)
        checkbox_frame.pack(side=tk.LEFT)
        self.other_info_practice = tk.BooleanVar()
        self.other_info_learn = tk.BooleanVar()
        self.other_info_old = tk.BooleanVar()
        ttk.Checkbutton(checkbox_frame, text="Practice", variable=self.other_info_practice).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(checkbox_frame, text="Learn", variable=self.other_info_learn).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(checkbox_frame, text="Old Dance", variable=self.other_info_old).pack(side=tk.LEFT, padx=2)

        # Optionally, configure grid weights for spacing
        button_row.grid_columnconfigure(0, weight=0)
        button_row.grid_columnconfigure(1, weight=0)
        button_row.grid_columnconfigure(2, weight=1)

        row += 1

        # Song section with list on left and details on right
        ttk.Separator(data_frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2, sticky=tk.EW, pady=10)
        row += 1
        
        # Container for songs list and details
        songs_container = ttk.Frame(data_frame)
        songs_container.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=3)
        
        # Left side: Song list
        list_frame = ttk.Frame(songs_container)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10), anchor=tk.N)
        
        ttk.Label(list_frame, text="Song List").pack(anchor=tk.W, pady=(0, 5))
        
        # Listbox with scrollbar for songs
        list_scroll_frame = ttk.Frame(list_frame)
        list_scroll_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_scroll_frame, orient=tk.VERTICAL)
        self.songs_listbox = tk.Listbox(list_scroll_frame, height=6, width=40, 
                                        yscrollcommand=scrollbar.set, exportselection=False)
        scrollbar.config(command=self.songs_listbox.yview)
        self.songs_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.songs_listbox.bind('<<ListboxSelect>>', self._on_song_select)
        # Add arrow key navigation
        self.songs_listbox.bind('<Up>', self._on_listbox_key)
        self.songs_listbox.bind('<Down>', self._on_listbox_key)
        self.songs_listbox.bind('<Return>', self._on_listbox_key)
        
        # Right side: Song details
        details_frame = ttk.Frame(songs_container)
        details_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, anchor=tk.N, pady=(22, 0))
        
        # Configure grid to prevent resizing
        details_frame.grid_columnconfigure(0, weight=0, minsize=100)  # Fixed width for labels
        details_frame.grid_columnconfigure(1, weight=1)  # Expandable for entries
        
        detail_row = 0
        ttk.Label(details_frame, text="Song Name:", width=12).grid(row=detail_row, column=0, sticky=tk.W, pady=2)
        self.song_name_var = tk.StringVar()
        self.song_name_entry = ttk.Entry(details_frame, textvariable=self.song_name_var, width=40, state='readonly', takefocus=0)
        self.song_name_entry.grid(row=detail_row, column=1, sticky=tk.W, pady=2)
        detail_row += 1
        
        ttk.Label(details_frame, text="Artist:", width=12).grid(row=detail_row, column=0, sticky=tk.W, pady=2)
        self.artist_var = tk.StringVar()
        self.artist_entry = ttk.Entry(details_frame, textvariable=self.artist_var, width=40, state='readonly', takefocus=0)
        self.artist_entry.grid(row=detail_row, column=1, sticky=tk.W, pady=2)
        detail_row += 1
        
        ttk.Label(details_frame, text="Genre:", width=12).grid(row=detail_row, column=0, sticky=tk.W, pady=2)
        self.genre_var = tk.StringVar()
        self.genre_entry = ttk.Entry(details_frame, textvariable=self.genre_var, width=40, state='readonly', takefocus=0)
        self.genre_entry.grid(row=detail_row, column=1, sticky=tk.W, pady=2)
        detail_row += 1
        
        ttk.Label(details_frame, text="BPM:", width=12).grid(row=detail_row, column=0, sticky=tk.W, pady=2)
        self.bpm_var = tk.StringVar()
        self.bpm_entry = ttk.Entry(details_frame, textvariable=self.bpm_var, width=15, state='readonly', takefocus=0)
        self.bpm_entry.grid(row=detail_row, column=1, sticky=tk.W, pady=2)
        detail_row += 1
        
        # Spotify URL row - label always in grid with fixed width to prevent shifting
        self.spotify_url_label = ttk.Label(details_frame, text=" ", width=12)  # Space instead of empty to maintain height
        self.spotify_url_label.grid(row=detail_row, column=0, sticky=tk.W, pady=2)
        self.spotify_url_label_row = detail_row
        
        # Container for spotify buttons and URL entry - fixed position with grid
        spotify_container = ttk.Frame(details_frame)
        spotify_container.grid(row=detail_row, column=1, sticky=tk.W, pady=2)
        
        # Use grid inside container to maintain fixed positions
        self.spotify_url_var = tk.StringVar()
        self.spotify_url_entry = ttk.Entry(spotify_container, textvariable=self.spotify_url_var, width=35, state='readonly')
        self.spotify_url_entry.grid(row=0, column=0, padx=(0, 5))
        self.spotify_url_entry.grid_remove()  # Hide initially
        
        self.spotify_button = ttk.Button(spotify_container, text="Open in Spotify", command=self._open_spotify, width=15)
        self.spotify_button.grid(row=0, column=0, padx=(0, 5))  # Same position as URL entry
        
        detail_row += 1
        
        # Edit/Save button - in its own fixed row with fixed width
        button_row_frame = ttk.Frame(details_frame)
        button_row_frame.grid(row=detail_row, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        self.edit_songs_btn = ttk.Button(button_row_frame, text="Edit", command=self._toggle_song_editing, width=5)
        self.edit_songs_btn.grid(row=0, column=0, padx=(0, 5))
        
        self.cancel_edit_btn = ttk.Button(button_row_frame, text="Cancel", command=self._cancel_song_editing, width=5)
        self.cancel_edit_btn.grid(row=0, column=1)
        self.cancel_edit_btn.grid_remove()  # Hidden by default
        
        # Configure uniform row heights to prevent vertical shifting
        for i in range(detail_row + 1):
            details_frame.grid_rowconfigure(i, uniform="row", minsize=30)
        
        row += 1
        
        # Action buttons
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="Save to Database", command=self._save_to_db).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Clear Form", command=self._clear_form).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Open Main GUI", command=self._open_main_gui).pack(side=tk.RIGHT, padx=5)
        
        # Track editing state
        self.songs_editable = False
    
    def _setup_combobox_behavior(self, combo, var):
        """Custom Combobox: empty option only in entry, not menu."""
        # Remove empty string from values if present
        values = list(combo.cget('values'))
        if values and values[0] == "":
            values = values[1:]
            combo['values'] = values

        combo._stored_value = ''
        combo._dropdown_open = False
        combo._entry_cleared = False

        def entry_widget():
            try:
                for child in combo.winfo_children():
                    if isinstance(child, tk.Entry):
                        return child
                return combo.nametowidget(combo.winfo_children()[0].winfo_pathname(combo.winfo_children()[0].winfo_id()))
            except Exception:
                return None

        def clear_entry_selection():
            entry = entry_widget()
            if entry:
                entry.selection_clear()
                entry.icursor('end')

        def on_dropdown_open():
            # Store the current value
            combo._stored_value = var.get()
            combo.set("")  # Show entry as empty (acts as empty option)
            combo._dropdown_open = True
            combo._entry_cleared = False
            entry = entry_widget()
            if entry:
                # If user clicks entry while menu is open and entry is empty, treat as clear
                def entry_click(ev):
                    if combo._dropdown_open and not combo.get():
                        combo._entry_cleared = True
                entry.bind('<Button-1>', entry_click, add='+')
                combo._entry_click = entry_click

        def on_dropdown_close(event=None):
            combo._dropdown_open = False
            entry = entry_widget()
            if entry and hasattr(combo, '_entry_click'):
                entry.unbind('<Button-1>', combo._entry_click)
                del combo._entry_click
            # If entry was cleared, clear var
            if combo._entry_cleared or not combo.get():
                var.set("")
                combo.set("")
                combo._stored_value = ""
                combo._entry_cleared = False
            else:
                var.set(combo.get())
                combo._stored_value = combo.get()

        def on_select(event):
            selected = combo.get()
            var.set(selected)
            combo._stored_value = selected
            clear_entry_selection()
            self.focus_set()
            combo._entry_cleared = False
            on_dropdown_close()

        def on_focus_out(event):
            # If entry was cleared, keep cleared
            if combo._entry_cleared or not combo.get():
                var.set("")
                combo.set("")
                combo._stored_value = ""
                combo._entry_cleared = False
            else:
                var.set(combo.get())
                combo._stored_value = combo.get()
            self.focus_set()
            on_dropdown_close()

        def on_focus_in(event):
            self.focus_set()

        combo.configure(postcommand=on_dropdown_open)
        combo.bind('<<ComboboxSelected>>', on_select)
        combo.bind('<FocusOut>', on_focus_out)
        combo.bind('<FocusIn>', on_focus_in)
        combo.bind('<Escape>', on_dropdown_close)
    
    def _on_song_select(self, event):
        """Handle song selection from the listbox."""
        selection = self.songs_listbox.curselection()
        if selection:
            index = selection[0]
            self._display_song_at_index(index)
    
    def _toggle_song_editing(self):
        """Toggle song field editing."""
        if self.songs_editable:
            # Save and disable editing
            self._save_current_song_edits()
            self.song_name_entry.config(state='readonly', takefocus=0)
            self.artist_entry.config(state='readonly', takefocus=0)
            self.genre_entry.config(state='readonly', takefocus=0)
            self.bpm_entry.config(state='readonly', takefocus=0)
            self.spotify_url_entry.config(state='readonly')
            # Hide Spotify URL field and label text, show Spotify button
            self.spotify_url_entry.grid_remove()
            self.spotify_url_label.config(text=" ")  # Space instead of empty to maintain height
            # Re-enable and show Spotify button if there's a URL
            if self.spotify_url_var.get().strip():
                self.spotify_button.config(state='normal')
            self.spotify_button.grid(row=0, column=0, padx=(0, 5))
            self.edit_songs_btn.config(text="Edit")
            # Hide cancel button
            self.cancel_edit_btn.grid_remove()
            self.songs_editable = False
        else:
            # Store original values before editing
            self._store_original_values()
            # Enable editing and show Spotify URL field, hide Spotify button
            self.song_name_entry.config(state='normal', takefocus=1)
            self.artist_entry.config(state='normal', takefocus=1)
            self.genre_entry.config(state='normal', takefocus=1)
            self.bpm_entry.config(state='normal', takefocus=1)
            self.spotify_url_entry.config(state='normal')
            # Hide Spotify button and show URL field with label text for editing
            self.spotify_button.grid_remove()
            self.spotify_url_label.config(text="Spotify URL:")  # Set label text instead of gridding
            self.spotify_url_entry.grid(row=0, column=0, padx=(0, 5))
            self.edit_songs_btn.config(text="Save")
            # Show cancel button
            self.cancel_edit_btn.grid(row=0, column=1)
            self.songs_editable = True
    
    def _store_original_values(self):
        """Store the original values before editing."""
        self.original_song_name = self.song_name_var.get()
        self.original_artist = self.artist_var.get()
        self.original_genre = self.genre_var.get()
        self.original_bpm = self.bpm_var.get()
        self.original_spotify_url = self.spotify_url_var.get()
    
    def _cancel_song_editing(self):
        """Cancel editing and restore original values."""
        # Restore original values
        self.song_name_var.set(self.original_song_name)
        self.artist_var.set(self.original_artist)
        self.genre_var.set(self.original_genre)
        self.bpm_var.set(self.original_bpm)
        self.spotify_url_var.set(self.original_spotify_url)
        
        # Disable editing
        self.song_name_entry.config(state='readonly', takefocus=0)
        self.artist_entry.config(state='readonly', takefocus=0)
        self.genre_entry.config(state='readonly', takefocus=0)
        self.bpm_entry.config(state='readonly', takefocus=0)
        self.spotify_url_entry.config(state='readonly')
        
        # Hide Spotify URL field and label text, show Spotify button
        self.spotify_url_entry.grid_remove()
        self.spotify_url_label.config(text=" ")  # Space instead of empty to maintain height
        
        # Re-enable and show Spotify button if there's a URL
        if self.spotify_url_var.get().strip():
            self.spotify_button.config(state='normal')
        self.spotify_button.grid(row=0, column=0, padx=(0, 5))
        
        self.edit_songs_btn.config(text="Edit")
        # Hide cancel button
        self.cancel_edit_btn.grid_remove()
        self.songs_editable = False
    
    def _save_current_song_edits(self):
        """Save the current song field edits back to extracted_data."""
        if not self.extracted_data or 'songs' not in self.extracted_data:
            return
        
        selection = self.songs_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        songs = self.extracted_data.get('songs', [])
        if 0 <= index < len(songs):
            # Update the song in extracted_data
            songs[index]['song_name'] = self.song_name_var.get().strip()
            songs[index]['artist'] = self.artist_var.get().strip()
            songs[index]['artist_display'] = self.artist_var.get().strip().replace(', ', ' & ')  # Convert back to & for display
            songs[index]['genre'] = self.genre_var.get().strip()
            bpm_str = self.bpm_var.get().strip()
            songs[index]['bpm'] = int(bpm_str) if bpm_str.isdigit() else None
            songs[index]['spotify_url'] = self.spotify_url_var.get().strip()
            
            # Update the listbox display using artist_display
            song_name = songs[index].get('song_name') or 'Unknown'
            artist_display = songs[index].get('artist_display') or 'Unknown'
            self.songs_listbox.delete(index)
            self.songs_listbox.insert(index, f"{song_name} - {artist_display}")
            self.songs_listbox.selection_set(index)
    
    def _on_listbox_key(self, event):
        """Handle keyboard navigation in the listbox."""
        # The listbox handles the selection change, we just need to update the display
        # Use after_idle to ensure the selection has been updated
        self.after_idle(lambda: self._on_song_select(event))
    
    def _display_song_at_index(self, index):
        """Display the song details for the given index."""
        if not self.extracted_data or 'songs' not in self.extracted_data:
            return
        
        songs = self.extracted_data.get('songs', [])
        if 0 <= index < len(songs):
            song = songs[index]
            self.song_name_var.set(song.get('song_name') or '')
            self.artist_var.set(song.get('artist') or '')
            # Filter out "-" placeholder
            genre = song.get('genre') or ''
            self.genre_var.set(genre if genre != '-' else '')
            bpm = song.get('bpm')
            self.bpm_var.set(str(bpm) if bpm else '')
            spotify_url = song.get('spotify_url') or ''
            self.spotify_url_var.set(spotify_url)
            # Enable/disable Spotify button based on URL availability
            if spotify_url:
                self.spotify_button.config(state='normal')
            else:
                self.spotify_button.config(state='disabled')
    
    def _open_spotify(self):
        """Open the Spotify URL in the Spotify app."""
        url = self.spotify_url_var.get().strip()
        if url:
            import subprocess
            # Convert web URL to spotify: URI if needed
            if 'open.spotify.com' in url or 'spotify.com' in url:
                # Extract track/album/playlist ID from URL
                # URLs look like: https://open.spotify.com/track/ID or https://open.spotify.com/album/ID
                parts = url.rstrip('/').split('/')
                if len(parts) >= 2:
                    resource_type = parts[-2]  # track, album, playlist, etc.
                    resource_id = parts[-1].split('?')[0]  # Remove query params
                    spotify_uri = f"spotify:{resource_type}:{resource_id}"
                    try:
                        subprocess.run(['open', spotify_uri], check=True)
                        return
                    except Exception as e:
                        print(f"Failed to open Spotify URI: {e}")
            # Fallback to opening URL directly
            subprocess.run(['open', url])
    
    def _open_stepsheet(self):
        """Open the Copperknob step sheet URL in a web browser."""
        if self.stepsheet_url:
            import webbrowser
            webbrowser.open(self.stepsheet_url)
    
    def _download_pdf(self):
        """Download PDF silently using headless browser or open if already downloaded."""
        if not self.pdf_url:
            return
        
        # If PDF already downloaded, just open it
        if self.pdf_path and os.path.exists(self.pdf_path):
            import subprocess
            # Use AppleScript to open in Preview and bring to front immediately
            script = f'tell application "Preview" to open POSIX file "{self.pdf_path}"\ntell application "Preview" to activate'
            subprocess.run(['osascript', '-e', script], check=False)
            return
        
        import threading
        def download():
            try:
                from selenium import webdriver
                from selenium.webdriver.firefox.options import Options
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                import time
                import glob
                import subprocess
                
                # Use pdfs subfolder in DanceDB directory
                # Always use top-level DanceDB/pdfs folder
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                download_dir = os.path.join(project_root, 'pdfs')
                os.makedirs(download_dir, exist_ok=True)
                
                options = Options()
                options.add_argument('-headless')
                options.set_preference('browser.download.folderList', 2)
                options.set_preference('browser.download.dir', download_dir)
                options.set_preference('browser.helperApps.neverAsk.saveToDisk', 'application/pdf')
                options.set_preference('pdfjs.disabled', True)
                
                driver = webdriver.Firefox(options=options)
                driver.set_page_load_timeout(10)
                
                try:
                    # Get list of PDFs before download
                    before_pdfs = set(glob.glob(os.path.join(download_dir, '*.pdf')))
                    
                    driver.get(self.pdf_url)
                    wait = WebDriverWait(driver, 10)
                    
                    # Try to find and click PDF download button
                    selectors = [
                        "//a[contains(text(), 'PDF')]",
                        "//button[contains(text(), 'PDF')]",
                        "//input[@value='PDF']"
                    ]
                    
                    for selector in selectors:
                        try:
                            elem = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                            elem.click()
                            time.sleep(3)  # Wait for download
                            break
                        except:
                            continue
                    
                    # Find the new PDF file
                    after_pdfs = set(glob.glob(os.path.join(download_dir, '*.pdf')))
                    new_pdfs = after_pdfs - before_pdfs
                    
                    if new_pdfs:
                        latest_pdf = max(new_pdfs, key=os.path.getctime)
                        
                        # Rename PDF to include stepsheet ID for easy future lookup
                        import re
                        match = re.search(r'/stepsheets/(\d+)/', self.pdf_url)
                        if match:
                            stepsheet_id = match.group(1)
                            dance_name = self.dance_name_var.get().strip()
                            # Create a clean filename
                            if dance_name:
                                # Remove special characters from dance name
                                clean_name = re.sub(r'[^\w\s-]', '', dance_name)
                                clean_name = re.sub(r'[-\s]+', '_', clean_name)
                                new_filename = f"{stepsheet_id}_{clean_name}.pdf"
                            else:
                                new_filename = f"{stepsheet_id}.pdf"
                            
                            new_path = os.path.join(download_dir, new_filename)
                            
                            # Rename if not already named correctly
                            if latest_pdf != new_path:
                                try:
                                    import shutil
                                    shutil.move(latest_pdf, new_path)
                                    latest_pdf = new_path
                                except:
                                    pass  # Keep original name if rename fails
                        
                        self.pdf_path = latest_pdf
                        # Change button text to "Open PDF"
                        self.pdf_button.config(text='Open PDF')
                        # Use AppleScript to open in Preview and bring to front immediately
                        script = f'tell application "Preview" to open POSIX file "{latest_pdf}"\ntell application "Preview" to activate'
                        subprocess.run(['osascript', '-e', script], check=False)
                    
                finally:
                    driver.quit()
                    
            except Exception as e:
                print(f"PDF download error: {e}")
        
        threading.Thread(target=download, daemon=True).start()
    

    
    def _log(self, message: str):
        """Log message - status box removed, this is now a no-op."""
        pass
    
    def _fetch_data(self):
        global re
        # DEBUG: Check if 're' is available
        try:
            print(f"DEBUG: re module is {re}")
        except Exception as e:
            print(f"DEBUG: re is not available: {e}")
            raise ImportError("re module is not available in _fetch_data")
        """Fetch and parse data from the provided URL."""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("No URL", "Please enter a Copperknob URL.")
            return
        
        if 'copperknob' not in url.lower():
            messagebox.showwarning("Invalid URL", "URL must be from copperknob.co.uk")
            return
        
        self._log(f"Fetching data from: {url}")
        self.fetch_btn.config(state='disabled')
        
        try:
            data = self.importer.extract_dance_data(url)
            
            if not data:
                self._log("❌ Failed to extract data from URL")
                messagebox.showerror("Extraction Failed", "Could not extract data from the provided URL.")
                return
            
            # Populate the form fields
            # Determine all possible names (main + aka), splitting main_name on 'Aka' as well
            main_name = data.get('dance_name') or ''
            aka = data.get('aka', '')
            print(f"DEBUG: main_name='{main_name}', aka='{aka}'")
            all_names = []
            # Split main_name on 'Aka' (case-insensitive) and other delimiters
            main_name_split = [n.strip() for n in re.split(r',|/|;|\band\b|\baka\b', main_name, flags=re.IGNORECASE) if n.strip()]
            print(f"DEBUG: main_name_split after split: {main_name_split}")
            all_names.extend(main_name_split)
            if aka:
                aka_names = [n.strip() for n in re.split(r',|/|;|\band\b|\baka\b', aka, flags=re.IGNORECASE) if n.strip()]
                print(f"DEBUG: aka_names after split: {aka_names}")
                all_names.extend(aka_names)
            # Remove duplicates, preserve order
            seen = set()
            unique_names = []
            for n in all_names:
                if n and n not in seen:
                    unique_names.append(n)
                    seen.add(n)
            print(f"DEBUG: unique_names for dropdown: {unique_names}")

            # Remove all widgets from the input frame
            for widget in self.dance_name_input_frame.winfo_children():
                widget.destroy()
            # Always use a new StringVar for dance_name_var to avoid stale bindings
            new_dance_name_var = tk.StringVar()
            if len(unique_names) > 1:
                print("DEBUG: Switching to dropdown for dance name")
                new_dance_name_var.set(unique_names[0])
                self.dance_name_combo = ttk.Combobox(self.dance_name_input_frame, textvariable=new_dance_name_var, width=43, state='readonly')
                self.dance_name_combo['values'] = unique_names
                self.dance_name_combo.grid(row=0, column=0, sticky="nsew")
                self._setup_combobox_behavior(self.dance_name_combo, new_dance_name_var)
            else:
                print("DEBUG: Using entry for dance name")
                new_dance_name_var.set(unique_names[0] if unique_names else '')
                self.dance_name_entry = ttk.Entry(self.dance_name_input_frame, textvariable=new_dance_name_var, width=43)
                self.dance_name_entry.grid(row=0, column=0, sticky="nsew")
            self.dance_name_var = new_dance_name_var
            self.aka_var.set(aka)
            
            # Format choreographers as "Name (Location), Name2 (Location2)"
            choreo_list = data.get('choreographers', [])
            if choreo_list:
                choreo_str = ', '.join([
                    f"{c['name']} ({c['location']})" if c['location'] else c['name']
                    for c in choreo_list
                ])
                self.choreographer_var.set(choreo_str)
            else:
                self.choreographer_var.set('')
            
            self.release_date_var.set(data.get('release_date') or '')
            self.level_var.set(data.get('level') or '')
            self.count_var.set(str(data.get('count') or ''))
            self.walls_var.set(str(data.get('walls') or ''))
            self.tags_var.set(str(data.get('tags') or ''))
            self.restarts_var.set(str(data.get('restarts') or ''))
            
            # Set extracted_data FIRST so _display_song_at_index can access it
            self.extracted_data = data
            
            # Populate songs list and select first song
            songs = data.get('songs', [])
            self.songs_listbox.delete(0, tk.END)  # Clear existing items
            
            if songs and len(songs) > 0:
                # Populate the listbox with "Song Name - Artist" using artist_display for original format
                for song in songs:
                    artist_display = song.get('artist_display', song.get('artist', 'Unknown'))
                    song_display = f"{song.get('song_name', 'Unknown')} - {artist_display}"
                    self.songs_listbox.insert(tk.END, song_display)
                
                # Select the first song by default
                self.songs_listbox.select_set(0)
                self._display_song_at_index(0)
                # Set focus to the listbox so arrow keys work immediately
                self.songs_listbox.focus_set()
            else:
                # Clear song fields if no songs
                self.song_name_var.set('')
                self.artist_var.set('')
                self.genre_var.set('')
                self.bpm_var.set('')
                self.spotify_url_var.set('')
                self.spotify_button.config(state='disabled')
            
            # Set step sheet URL and enable button
            if data.get('url'):
                self.stepsheet_url = data['url']
                self.stepsheet_button.config(state='normal')
                self.pdf_url = data['url']
                
                # Extract and store copperknob_id from URL
                import re
                match = re.search(r'/stepsheets/(\d+)/', data['url'])
                if match:
                    self.copperknob_id = match.group(1)
                
                # Check if we already have a PDF for this URL using the copperknob_id
                if self.copperknob_id:
                    # Look for PDF with this ID in pdfs folder
                    # Always use top-level DanceDB/pdfs folder
                    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    download_dir = os.path.join(project_root, 'pdfs')
                    import glob
                    # Common Copperknob PDF naming patterns
                    possible_patterns = [
                        os.path.join(download_dir, f'*{self.copperknob_id}*.pdf'),
                        os.path.join(download_dir, f'{self.copperknob_id}.pdf'),
                    ]
                    
                    found_pdf = None
                    for pattern in possible_patterns:
                        matches = glob.glob(pattern)
                        if matches:
                            # Get the most recent if multiple matches
                            found_pdf = max(matches, key=os.path.getctime)
                            break
                    
                    if found_pdf and os.path.exists(found_pdf):
                        self.pdf_path = found_pdf
                        self.pdf_button.config(state='normal', text='Open PDF')
                    else:
                        self.pdf_path = None
                        self.pdf_button.config(state='normal', text='Download PDF')
                else:
                    self.pdf_path = None
                    self.pdf_button.config(state='normal', text='Download PDF')
            else:
                self.stepsheet_url = ""
                self.stepsheet_button.config(state='disabled')
                self.pdf_url = ""
                self.pdf_path = None
                self.pdf_button.config(state='disabled', text='Download PDF')
            
            self._log("✓ Successfully extracted data!")
            self._log(f"  Dance: {data.get('dance_name')}")
            
            songs = data.get('songs', [])
            if songs:
                if len(songs) == 1:
                    song = songs[0]
                    self._log(f"  Song: {song.get('song_name')} by {song.get('artist')}")
                    if song.get('genre'):
                        self._log(f"  Genre: {song.get('genre')}")
                    if song.get('bpm'):
                        self._log(f"  BPM: {song.get('bpm')}")
                else:
                    self._log(f"  Found {len(songs)} songs:")
                    for i, song in enumerate(songs, 1):
                        self._log(f"    {i}. {song.get('song_name')} by {song.get('artist')}")
            else:
                self._log("  (No song data found - you can enter it manually)")
            
        except Exception as e:
            self._log(f"❌ Error: {e}")
            messagebox.showerror("Error", f"An error occurred: {e}")
        finally:
            self.fetch_btn.config(state='normal')
    
    def _save_to_db(self):
        """Save the extracted/edited data to the database."""
        dance_name = self.dance_name_var.get().strip()
        if not dance_name:
            messagebox.showwarning("Missing Data", "Dance name is required.")
            return
        
        # Parse choreographers from the text field
        # Expected format: "Name (Location) & Name2 (Location2)" or just "Name & Name2"
        choreo_text = self.choreographer_var.get().strip()
        choreographers = []
        if choreo_text:
            # Split by & or 'and' or comma
            choreo_parts = re.split(r'\s*(?:,\s*(?:and\s+)?|&\s*|(?:\s+and\s+))\s*', choreo_text)
            choreo_parts = [p.strip() for p in choreo_parts if p.strip()]
            for part in choreo_parts:
                match = re.match(r'([^(]+)(?:\(([^)]+)\))?', part.strip())
                if match:
                    name = match.group(1).strip()
                    location = match.group(2).strip() if match.group(2) else ''
                    choreographers.append({
                        'name': name,
                        'location': location
                    })
        
        # Build the dance record
        # Build other_info from checkboxes
        other_info_items = []
        if self.other_info_learn.get():
            other_info_items.append("Learn")
        if self.other_info_practice.get():
            other_info_items.append("Practice")
        if self.other_info_old.get():
            other_info_items.append("Old Dance")
        
        record = {
            'name': dance_name,
            'aka': self.aka_var.get().strip(),
            'level': self.level_var.get().strip(),
            'choreographers': json.dumps(choreographers),
            'release_date': self.release_date_var.get().strip(),
            'notes': self.notes_text.get('1.0', 'end-1c'),
            'copperknob_id': self.copperknob_id if self.copperknob_id else '',
            'priority': self.priority_var.get().strip(),
            'known': self.known_var.get().strip(),
            'category': self.category_var.get().strip(),
            'other_info': ', '.join(other_info_items),
            'frequency': self.frequency_var.get().strip()
        }
        
        # Build song data - use extracted data if available, otherwise build from GUI fields
        songs = []
        if self.extracted_data and 'songs' in self.extracted_data:
            # Use the full songs list from the extracted data
            songs = self.extracted_data.get('songs', [])
            print(f"DEBUG: Using extracted songs list: {len(songs)} song(s)")
        else:
            # Fallback: build from single song GUI fields
            song_name = self.song_name_var.get().strip()
            if song_name:
                song = {
                    'name': song_name,
                    'artist': self.artist_var.get().strip()
                }
                genre = self.genre_var.get().strip()
                if genre:
                    song['genre'] = genre
                bpm_str = self.bpm_var.get().strip()
                if bpm_str:
                    try:
                        song['bpm'] = float(bpm_str)
                    except ValueError:
                        pass
                spotify_url = self.spotify_url_var.get().strip()
                if spotify_url:
                    song['spotify_url'] = spotify_url
                songs.append(song)
        
        record['songs'] = json.dumps(songs)
        print(f"DEBUG: Saving {len(songs)} song(s) to database")
        
        try:
            self.db.add_record(record)
            self._log(f"✓ Saved '{dance_name}' to database!")
            messagebox.showinfo("Saved", f"Dance '{dance_name}' has been saved to the database.")
            self._clear_form()
        except Exception as e:
            self._log(f"❌ Error saving: {e}")
            messagebox.showerror("Save Error", f"Failed to save: {e}")
    
    def _clear_form(self):
        # Revert dance name input to Entry (text box)
        for widget in self.dance_name_input_frame.winfo_children():
            widget.destroy()
        self.dance_name_var = tk.StringVar()
        self.dance_name_entry = ttk.Entry(self.dance_name_input_frame, textvariable=self.dance_name_var, width=43)
        self.dance_name_entry.grid(row=0, column=0, sticky="nsew")
        """Clear all form fields."""
        self.url_var.set('')
        self.dance_name_var.set('')
        self.choreographer_var.set('')
        self.release_date_var.set('')
        self.level_var.set('')
        self.count_var.set('')
        self.walls_var.set('')
        self.tags_var.set('')
        self.restarts_var.set('')
        self.priority_var.set('')
        self.known_var.set('')
        self.category_var.set('')
        self.other_info_learn.set(False)
        self.other_info_practice.set(False)
        self.other_info_old.set(False)
        self.frequency_var.set('')
        self.songs_listbox.delete(0, tk.END)  # Clear songs list
        self.song_name_var.set('')
        self.artist_var.set('')
        self.genre_var.set('')
        self.bpm_var.set('')
        self.spotify_url_var.set('')
        self.spotify_button.config(state='disabled')
        self.stepsheet_url = ""
        self.copperknob_id = None
        self.stepsheet_button.config(state='disabled')
        self.pdf_url = ""
        self.pdf_path = None
        self.pdf_button.config(state='disabled', text='Download PDF')
        self.extracted_data = None
    
    def _open_main_gui(self):
        """Open the main dance management GUI."""
        import subprocess
        import sys
        import os
        # Find the absolute path to dance_gui.py in the same project (assume src/dance_gui.py)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        gui_path = os.path.join(project_root, 'src', 'dance_gui.py')
        if not os.path.exists(gui_path):
            from tkinter import messagebox
            messagebox.showerror("Not Found", f"Could not find main GUI at {gui_path}")
            return
        subprocess.Popen([sys.executable, gui_path])


def main():
    app = CopperknobImportGUI()
    app.mainloop()


if __name__ == '__main__':
    main()
