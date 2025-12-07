#!/usr/bin/env python3
"""Test URL generation to see if there's an encoding issue."""

from urllib.parse import urlencode
import sys

# Simulate what the app does
client_id = "test_client_id_1234567890abcdef"  # Example valid-looking ID
scope = "user-read-private user-library-read"

auth_params = {
    'client_id': client_id,
    'response_type': 'code',
    'redirect_uri': 'http://127.0.0.1:8888/callback',
    'scope': scope
}

auth_url = f"https://accounts.spotify.com/authorize?{urlencode(auth_params)}"

print("Generated URL:")
print(auth_url)
print()

# Try to open it with Python's webbrowser
import webbrowser
print("Attempting to open with webbrowser.open()...")
try:
    result = webbrowser.open(auth_url)
    print(f"Result: {result}")
    if result:
        print("✓ Browser should have opened")
    else:
        print("✗ webbrowser.open returned False")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print()
print("If the browser didn't open, try pasting this into your browser manually:")
print(auth_url)
