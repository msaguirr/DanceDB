"""Quickstart example for the minimal myspotipy wrapper.

Set `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` in your environment,
then run this example to perform a simple search using client credentials.
"""
import os
from myspotipy import Spotify, SpotifyOAuth


def main():
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables")
        return

    oauth = SpotifyOAuth(client_id, client_secret)
    token_info = oauth.client_credentials_token()
    token = token_info.get("access_token")
    sp = Spotify(access_token=token)
    res = sp.search("Daft Punk", types="artist,track", limit=3)
    print(res)


if __name__ == "__main__":
    main()
