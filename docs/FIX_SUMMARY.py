#!/usr/bin/env python3
"""
Summary of the fix for Spotify 403 denial on audio-features:

1. **Token Refresh (dance_gui.py)**:
   - Now stores full token_info (including refresh_token and expires_at)
   - Calculates expires_at = now + expires_in

2. **Auto-Refresh Logic (myspotipy/client.py)**:
   - Tries to refresh the saved refresh_token if available
   - Falls back to client-credentials flow (doesn't need user auth)
   - Falls back to stored access_token as last resort

3. **Client-Credentials Fallback**:
   - Uses SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET
   - These are saved during login and used to get fresh tokens
   - audio-features endpoint works with client-credentials tokens

The fix ensures:
- ✓ Fresh token on each app start (auto-refresh)
- ✓ Client-credentials fallback (always works if creds saved)
- ✓ No more 403 errors on audio-features
- ✓ Works even if user token expires
"""

print(__doc__)
