#!/usr/bin/env python3
"""Debug script to inspect Copperknob page structure."""

import requests
from bs4 import BeautifulSoup
import re
import sys

def debug_page(url):
    """Fetch and analyze a Copperknob page."""
    print(f"Fetching: {url}")
    print("=" * 80)
    
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        print("\n1. ALL LINKS on the page:")
        print("-" * 80)
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            text = link.get_text(strip=True)[:50]
            print(f"  {href[:60]:<60} | {text}")
        
        print("\n\n2. LINKS containing 'song' or 'music':")
        print("-" * 80)
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            text = link.get_text(strip=True)
            if 'song' in href.lower() or 'music' in href.lower() or 'music' in text.lower():
                print(f"  HREF: {href}")
                print(f"  TEXT: {text}")
                print()
        
        print("\n\n3. TEXT containing 'music', 'song', 'artist':")
        print("-" * 80)
        page_text = soup.get_text()
        for line in page_text.split('\n'):
            line = line.strip()
            if line and any(word in line.lower() for word in ['music', 'song', 'artist', 'bpm']):
                print(f"  {line[:120]}")
        
        print("\n\n4. STRUCTURED DATA (div/span with classes):")
        print("-" * 80)
        for elem in soup.find_all(['div', 'span', 'p'], class_=True):
            classes = ' '.join(elem.get('class', []))
            text = elem.get_text(strip=True)[:80]
            if text and any(word in text.lower() for word in ['music', 'song', 'artist', 'bpm', 'choreographer']):
                print(f"  <{elem.name} class='{classes}'>")
                print(f"    {text}")
                print()
        
        print("\n\n5. First 2000 characters of raw HTML:")
        print("-" * 80)
        print(resp.text[:2000])
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Enter Copperknob URL (step sheet page): ").strip()
    
    if url:
        debug_page(url)
    else:
        print("Usage: python debug_copperknob.py <url>")
        print("Or run without args and enter URL when prompted")
