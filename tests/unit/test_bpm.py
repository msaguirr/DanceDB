#!/usr/bin/env python3
"""Quick helper script to test Spotify audio-features (tempo -> bpm).

Usage: set `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` in env or
have them in `~/.myspotipy/config.json`. Then run:

  .venv/bin/python test_bpm.py <spotify_track_id>

If no track id is provided the script will prompt.

The script will attempt:
 - use global Spotify client (if any) to fetch audio-features
 - use client-credentials fallback to fetch audio-features

It prints the raw audio-features JSON and the `tempo` value (mapped to `bpm`).
"""
import os
import sys
import json

from myspotipy.client import get_global_spotify


def try_with_global(track_id):
    try:
        # prefer creating a global spotify client (may prompt user to authenticate)
        sp = get_global_spotify(create_if_missing=True)
    except Exception:
        sp = None
    if sp is None:
        print('No global spotify client available')
        return None
    try:
        af = sp.audio_features([track_id])
        print('Global client audio_features response (raw):')
        print(repr(af))
        # try to print any attached raw metadata (if client wrapper exposes it)
        try:
            if hasattr(af, 'status_code'):
                print('status_code:', af.status_code)
        except Exception:
            pass
        if af and af[0] is not None:
            print('tempo ->', af[0].get('tempo'))
            return af[0].get('tempo')
    except Exception as e:
        print('Global client error:', repr(e))
    return None


def try_with_client_credentials(track_id):
    try:
        # try to read creds from env or config
        client_id = os.getenv('SPOTIFY_CLIENT_ID')
        client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        if not client_id or not client_secret:
            cfg_path = os.path.join(os.path.expanduser('~'), '.myspotipy', 'config.json')
            if os.path.exists(cfg_path):
                try:
                    with open(cfg_path, 'r', encoding='utf-8') as f:
                        cfg = json.load(f)
                    def _maybe_b64(s):
                        if not s:
                            return s
                        try:
                            return __import__('base64').b64decode(s).decode()
                        except Exception:
                            return s
                    client_id = client_id or _maybe_b64(cfg.get('client_id'))
                    client_secret = client_secret or _maybe_b64(cfg.get('client_secret'))
                except Exception:
                    pass
        if not client_id or not client_secret:
            print('No client credentials available in env or config')
            return None
        from myspotipy.oauth import SpotifyOAuth
        from myspotipy.client import Spotify
        oauth = SpotifyOAuth(client_id, client_secret)
        token_info = oauth.client_credentials_token()
        print('client-credentials token_info (raw):')
        print(repr(token_info))
        token = token_info.get('access_token')
        if not token:
            print('client-credentials did not return token')
            return None
        # attempt a direct HTTP request to the Web API to capture raw response
        try:
            import requests
            url = f'https://api.spotify.com/v1/audio-features/{track_id}'
            headers = {'Authorization': f'Bearer {token}'}
            resp = requests.get(url, headers=headers, timeout=10)
            print('Direct HTTP request status:', resp.status_code)
            try:
                print('Direct HTTP response body:', resp.text)
            except Exception:
                print('Direct response body unavailable')
        except Exception as e:
            print('Direct HTTP request failed:', repr(e))

        sp = Spotify(access_token=token)
        try:
            af = sp.audio_features([track_id])
            print('Client-credentials audio_features response (raw):')
            print(repr(af))
        except Exception as e:
            print('client-credentials error:', repr(e))
            af = None
        if af and af[0] is not None:
            print('tempo ->', af[0].get('tempo'))
            return af[0].get('tempo')
    except Exception as e:
        print('client-credentials error:', repr(e))
    return None


def main():
    if len(sys.argv) > 1:
        tid = sys.argv[1]
    else:
        tid = input('Spotify track id: ').strip()
    if not tid:
        print('No track id provided')
        sys.exit(2)
    print('Track id:', tid)
    g = try_with_global(tid)
    if g is not None:
        print('Global client tempo:', g)
    c = try_with_client_credentials(tid)
    if c is not None:
        print('Client credentials tempo:', c)


if __name__ == '__main__':
    main()
