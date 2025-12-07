#!/usr/bin/env python3
"""
SPOTIFY LOGIN SETUP GUIDE
==========================

If you're getting "server cannot connect" error when trying to login,
follow these steps carefully.

STEP 1: Create a Spotify Developer App
======================================
1. Go to https://developer.spotify.com/dashboard
2. Log in with your Spotify account (create one if needed)
3. Click "Create an App"
4. Accept the terms and click "Create"
5. You'll see a new app with a Client ID and Client Secret
   - IMPORTANT: Keep these secret! Don't share them.
   - These are what the DanceDB app needs to connect to Spotify

STEP 2: Add Redirect URI to Your App
====================================
1. Go to your app settings (click the app name in the dashboard)
2. Click "Edit Settings"
3. Find "Redirect URIs" section
4. Add EXACTLY this (copy-paste it):
   http://127.0.0.1:8888/callback
5. Click "Save"
   - NOTE: It must be HTTP (not HTTPS)
   - NOTE: It must be 127.0.0.1 (not localhost or 0.0.0.0)
   - NOTE: The callback path must be /callback

STEP 3: Start the DanceDB App and Login
=======================================
1. Run: .venv/bin/python dance_gui.py
2. Click the "Login" button
3. When prompted:
   - Paste your Client ID (from dashboard)
   - Paste your Client Secret (from dashboard)
4. Click "Open Spotify Login"
5. You'll see a browser window open
6. Log in with your Spotify account
7. You'll be redirected to http://127.0.0.1:8888/callback?code=...
8. Copy the ENTIRE URL (including the code parameter)
9. Paste it into the DanceDB app
10. You should be logged in!

TROUBLESHOOTING: "Server Cannot Connect"
==========================================

If the browser says "server cannot connect" when you click "Open Spotify Login":

A) INVALID CLIENT ID
   - Make sure you copied the Client ID exactly from the dashboard
   - Don't type it manually - copy/paste only
   - The ID should be ~32 characters
   - Try again with a fresh copy from the dashboard

B) REDIRECT URI NOT REGISTERED
   - Go back to your app settings in Spotify dashboard
   - Make sure "http://127.0.0.1:8888/callback" is in the Redirect URIs list
   - Make sure you clicked "Save"
   - Wait a minute and try again

C) NETWORK/FIREWALL ISSUE
   - Try manually visiting https://accounts.spotify.com/authorize in your browser
   - If that works, go to developer.spotify.com and copy the link from there
   - If that doesn't work, you might have network issues

D) BROWSER NOT OPENING
   - The app will display the URL in the dialog
   - Click "Copy URL to Clipboard"
   - Manually paste it into your browser address bar
   - This should take you to the Spotify login page

QUICK START (if you already have credentials)
==============================================

Option 1: Environment Variables (preferred)
   export SPOTIFY_CLIENT_ID="your_client_id_here"
   export SPOTIFY_CLIENT_SECRET="your_client_secret_here"
   .venv/bin/python dance_gui.py

Option 2: Manual Entry
   Just click Login and enter when prompted

Option 3: Config File
   Create ~/.myspotipy/config.json with:
   {
     "client_id": "base64_encoded_client_id",
     "client_secret": "base64_encoded_client_secret"
   }

STILL HAVING ISSUES?
====================

Check the error log: ~/.myspotipy/auth_error.log
Run the diagnostics: .venv/bin/python diagnose_spotify.py

"""

print(__doc__)
