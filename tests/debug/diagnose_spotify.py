#!/usr/bin/env python3
"""Diagnostic script to check Spotify login setup."""

import os
import json
import base64
from urllib.parse import urlencode

# Check environment variables
cid = os.getenv('SPOTIFY_CLIENT_ID', '')
cs = os.getenv('SPOTIFY_CLIENT_SECRET', '')

print("=" * 60)
print("SPOTIFY LOGIN DIAGNOSTICS")
print("=" * 60)

print("\n1. Environment Variables:")
print(f"   SPOTIFY_CLIENT_ID: {'SET' if cid else 'NOT SET'}")
print(f"   SPOTIFY_CLIENT_SECRET: {'SET' if cs else 'NOT SET'}")

# Check config file
cfg_path = os.path.expanduser('~/.myspotipy/config.json')
print(f"\n2. Config File: {cfg_path}")
print(f"   Exists: {os.path.exists(cfg_path)}")

if os.path.exists(cfg_path):
    try:
        with open(cfg_path) as f:
            cfg = json.load(f)
        print(f"   Keys: {list(cfg.keys())}")
        
        def b64d(s):
            if not s:
                return None
            try:
                return base64.b64decode(s).decode()
            except:
                return s
        
        loaded_cid = b64d(cfg.get('client_id'))
        if loaded_cid:
            print(f"   Stored Client ID: {loaded_cid[:20]}...")
            cid = cid or loaded_cid
    except Exception as e:
        print(f"   Error reading config: {e}")

print(f"\n3. Final Client ID (to be used):")
if cid and len(cid) >= 10:
    print(f"   ✓ VALID: {cid[:20]}...")
else:
    print(f"   ✗ INVALID or MISSING: {repr(cid)}")

# Build example URL
print(f"\n4. Example Authorization URL:")
auth_params = {
    'client_id': cid or '[YOUR_CLIENT_ID]',
    'response_type': 'code',
    'redirect_uri': 'http://127.0.0.1:8888/callback',
    'scope': 'user-read-private user-library-read'
}
auth_url = f"https://accounts.spotify.com/authorize?{urlencode(auth_params)}"
print(f"   {auth_url[:80]}...")

print(f"\n5. How to fix 'server cannot connect' error:")
print("""
   a) Get Client ID from https://developer.spotify.com/dashboard
   b) Either:
      - Set env vars: export SPOTIFY_CLIENT_ID=<id> && export SPOTIFY_CLIENT_SECRET=<secret>
      - Or enter them when prompted by the GUI
   c) Make sure the URL shown in step 4 looks correct
   d) Try manually pasting it in the browser
""")

print("\n" + "=" * 60)
