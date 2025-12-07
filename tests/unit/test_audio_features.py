#!/usr/bin/env python3
"""Test audio features endpoint to debug 403 issues."""

import os
import json
import base64
from myspotipy.oauth import SpotifyOAuth
from myspotipy.client import Spotify, get_global_spotify

# Load config
cfg_path = os.path.expanduser('~/.myspotipy/config.json')
if not os.path.exists(cfg_path):
    print(f"No config found at {cfg_path}")
    print("Please log in via the GUI first, or set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET env vars")
    exit(1)

with open(cfg_path) as f:
    cfg = json.load(f)

def b64d(s):
    if not s:
        return None
    try:
        return base64.b64decode(s).decode()
    except:
        return s

client_id = b64d(cfg.get('client_id'))
client_secret = b64d(cfg.get('client_secret'))
access_token = b64d(cfg.get('access_token'))
token_info = cfg.get('token_info', {})

print(f"Client ID: {client_id[:20]}..." if client_id else "No Client ID")
print(f"Client Secret: {'*' * 10}" if client_secret else "No Client Secret")
print(f"Access Token: {access_token[:20]}..." if access_token else "No Access Token")
print(f"Token Info Keys: {list(token_info.keys())}")
print(f"Refresh Token: {token_info.get('refresh_token', 'MISSING')[:20]}..." if token_info.get('refresh_token') else "No Refresh Token")

# Now test using get_global_spotify which should handle all the logic
print("\n--- Using get_global_spotify() ---")
try:
    sp = get_global_spotify(create_if_missing=True)
    print(f"✓ Got global Spotify client")
    
    # First try a search to verify token works
    print("1. Testing search...")
    results = sp.search_tracks("Blinding Lights", k=1)
    if results:
        track_id = results[0]['id']
        print(f"   ✓ Search works! Found track: {results[0]['name']} (id={track_id})")
        
        # Now try audio features
        print(f"2. Testing audio-features for track {track_id}...")
        af = sp.audio_features([track_id])
        print(f"   Response: {af}")
        if af and af[0]:
            print(f"   ✓ Audio features retrieved! BPM: {af[0].get('tempo')}")
        else:
            print(f"   ✗ No audio features in response")
    else:
        print("   ✗ Search returned no results")
        
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()
