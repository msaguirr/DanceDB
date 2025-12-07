#!/usr/bin/env python3
"""BPM fetcher with multiple sources including Copperknob-style lookup.

Since Copperknob's search API structure may vary, this module provides:
1. A local BPM database for common line dance songs
2. Web scraping fallback (when available)
3. Easy extension for other BPM sources
"""
import requests
from typing import Optional, Dict
import re
from bs4 import BeautifulSoup


# Common line dance songs with known BPM
# This can be extended as you add more songs
BPM_DATABASE = {
    # Format: "song name - artist": bpm
    "boot scootin' boogie - brooks & dunn": 130,
    "achy breaky heart - billy ray cyrus": 120,
    "copperhead road - steve earle": 142,
    "electric slide - marcia griffiths": 118,
    "watermelon crawl - tracy byrd": 124,
    "tush push - various": 120,
    "cowboy charleston - various": 88,
    "country girl shake - luke bryan": 130,
    "wagon wheel - darius rucker": 90,
}


class CopperknobScraper:
    """Fetch BPM from multiple sources including local database and web scraping."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def search_song(self, song_name: str, artist: Optional[str] = None) -> Optional[Dict]:
        """Search for a song and return BPM and other metadata.
        
        Tries multiple sources:
        1. Local BPM database (for common line dance songs)
        2. Web scraping (future enhancement)
        
        Args:
            song_name: Name of the song to search for
            artist: Optional artist name to narrow results
            
        Returns:
            Dictionary with keys: bpm, song_name, artist, source, url
            Returns None if not found
        """
        # Try local database first
        lookup_key = song_name.lower()
        if artist:
            lookup_key = f"{lookup_key} - {artist.lower()}"
        
        if lookup_key in BPM_DATABASE:
            return {
                'bpm': BPM_DATABASE[lookup_key],
                'song_name': song_name,
                'artist': artist,
                'source': 'local_database',
                'url': None
            }
        
        # Try with just song name if artist combo didn't work
        if artist and song_name.lower() in BPM_DATABASE:
            return {
                'bpm': BPM_DATABASE[song_name.lower()],
                'song_name': song_name,
                'artist': artist,
                'source': 'local_database',
                'url': None
            }
        
        # Future: Add web scraping here for Copperknob or other sources
        # For now, return None - user can manually enter BPM
        return None
    
    
    def search_dance(self, dance_name: str) -> Optional[Dict]:
        """Search for a dance and return metadata.
        
        Args:
            dance_name: Name of the dance to search for
            
        Returns:
            Dictionary with dance metadata
        """
        # Placeholder for future enhancement
        return None
    
    def add_to_database(self, song_name: str, artist: str, bpm: int):
        """Add a song BPM to the local database (in-memory for now).
        
        In a future version, this could persist to a JSON file.
        """
        lookup_key = f"{song_name.lower()} - {artist.lower()}"
        BPM_DATABASE[lookup_key] = bpm


def get_bpm_from_copperknob(song_name: str, artist: Optional[str] = None) -> Optional[float]:
    """Convenience function to fetch BPM for a song.
    
    Args:
        song_name: Name of the song
        artist: Optional artist name
        
    Returns:
        BPM as float, or None if not found
    """
    scraper = CopperknobScraper()
    result = scraper.search_song(song_name, artist)
    if result and 'bpm' in result:
        return float(result['bpm'])
    return None


if __name__ == '__main__':
    # Test the scraper
    import sys
    
    if len(sys.argv) > 1:
        song = sys.argv[1]
        artist = sys.argv[2] if len(sys.argv) > 2 else None
        
        scraper = CopperknobScraper()
        result = scraper.search_song(song, artist)
        
        if result:
            print(f"Found: {result}")
        else:
            print(f"No BPM found for '{song}'")
            print("You can manually add it using the 'Edit BPM' button in the app")
    else:
        print("Usage: python copperknob_scraper.py 'song name' ['artist']")
        print(f"\nCurrent database has {len(BPM_DATABASE)} songs")
