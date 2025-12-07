import urllib.parse
import requests

from .exceptions import SpotifyException


class Spotify:
    """Minimal Spotify Web API client.

    Construct with either an `access_token` or an `auth` helper (SpotifyOAuth).
    """

    API_BASE = "https://api.spotify.com/v1"

    def __init__(self, auth=None, access_token=None, session=None):
        if session is not None:
            self._session = session
        else:
            self._session = requests.Session()

        token = None
        if access_token:
            token = access_token
        elif auth is not None:
            token_info = auth.client_credentials_token()
            token = token_info.get("access_token")

        if not token:
            raise SpotifyException("No access token provided and no auth helper available")

        self._session.headers.update({"Authorization": f"Bearer {token}", "Accept": "application/json"})

    def _request(self, method, path, params=None, json=None):
        url = urllib.parse.urljoin(self.API_BASE + "/", path.lstrip("/"))
        r = self._session.request(method, url, params=params, json=json, timeout=10)
        if not r.ok:
            try:
                err = r.json()
            except Exception:
                r.raise_for_status()
            raise SpotifyException(err)
        return r.json()

    def search(self, q, types="track", limit=10, offset=0):
        params = {"q": q, "type": types, "limit": limit, "offset": offset}
        return self._request("GET", "/search", params=params)

    def search_tracks(self, song_name, artist=None, k=5):
        """Search for tracks by song name and optional artist and return up to k results.

        - song_name: the name (or partial name) of the song to search for.
        - artist: optional artist name to narrow results.
        - k: maximum number of track results to return (Spotify max per request is 50).

        Returns a list of simplified track dicts with keys: `id`, `name`, `artists`,
        `album`, `popularity`, `uri`, `preview_url`, `external_urls`.
        """
        # Build a Spotify query that uses field filters for better relevance.
        if artist:
            q = f"track:{song_name} artist:{artist}"
        else:
            q = f"track:{song_name}"

        limit = min(max(1, int(k)), 50)
        resp = self.search(q, types="track", limit=limit)
        items = []
        try:
            tracks = resp.get("tracks", {}).get("items", [])
        except Exception:
            tracks = []

        for t in tracks:
            artist_objs = t.get("artists", [])
            simplified = {
                "id": t.get("id"),
                "name": t.get("name"),
                # include both names and ids so callers can fetch genres by artist id
                "artist_ids": [a.get("id") for a in artist_objs if a.get("id")],
                "artists": [a.get("name") for a in artist_objs],
                "album": t.get("album", {}).get("name"),
                "popularity": t.get("popularity"),
                "uri": t.get("uri"),
                "preview_url": t.get("preview_url"),
                "external_urls": t.get("external_urls", {}),
                "raw": t,
            }
            items.append(simplified)

        return items

    def track(self, track_id):
        return self._request("GET", f"/tracks/{track_id}")

    def audio_features(self, ids):
        """Fetch audio features for one or more track IDs.

        Accepts a single id or an iterable of ids. Returns a list of audio feature
        objects (empty list if none found).
        """
        if not ids:
            return []
        if isinstance(ids, str):
            ids = [ids]
        ids = list(ids)
        # Spotify supports up to 100 ids per request
        chunk = ids[:100]
        resp = self._request("GET", "/audio-features", params={"ids": ",".join(chunk)})
        return resp.get("audio_features", [])

    def artists(self, ids):
        """Fetch artist objects for one or more artist IDs.

        Accepts a single id or an iterable of ids. Returns a list of artist
        objects (empty list if none found).
        """
        if not ids:
            return []
        if isinstance(ids, str):
            ids = [ids]
        ids = list(ids)
        chunk = ids[:50]
        resp = self._request("GET", "/artists", params={"ids": ",".join(chunk)})
        return resp.get("artists", [])


# Module-level global Spotify client instance and helpers to manage it.
_GLOBAL_SPOTIFY = None


def set_global_spotify(sp_instance):
    """Set the module-global Spotify client instance.

    Use this to inject an existing `Spotify` instance so callers don't have to pass
    it around.
    """
    global _GLOBAL_SPOTIFY
    _GLOBAL_SPOTIFY = sp_instance


def get_global_spotify(create_if_missing=True):
    """Return the module-global Spotify instance.

    If no global instance is set and `create_if_missing` is True, this will try to
    construct a client from `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` environment
    variables using the client credentials flow. If creation fails, raises
    `SpotifyException`.
    """
    global _GLOBAL_SPOTIFY
    if _GLOBAL_SPOTIFY is not None:
        return _GLOBAL_SPOTIFY
    if not create_if_missing:
        return None
    # Try to create from environment variables first
    import os

    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if client_id and client_secret:
        from .oauth import SpotifyOAuth

        oauth = SpotifyOAuth(client_id, client_secret)
        token_info = oauth.client_credentials_token()
        token = token_info.get("access_token")
        sp = Spotify(access_token=token)
        _GLOBAL_SPOTIFY = sp
        return sp

    # Fallback: try to read saved config from ~/.myspotipy/config.json
    try:
        cfg_path = os.path.join(os.path.expanduser("~"), ".myspotipy", "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                import json

                cfg = json.load(f)
            def _maybe_b64(s):
                if not s:
                    return s
                try:
                    return __import__("base64").b64decode(s).decode()
                except Exception:
                    return s

            access_token = _maybe_b64(cfg.get("access_token"))
            client_id = _maybe_b64(cfg.get("client_id"))
            client_secret = _maybe_b64(cfg.get("client_secret"))
            token_info = cfg.get("token_info", {})
            refresh_token = token_info.get("refresh_token") if isinstance(token_info, dict) else None

            # Try to refresh the access token if we have a refresh_token and client credentials
            if refresh_token and client_id and client_secret:
                try:
                    from .oauth import SpotifyOAuth
                    import time
                    
                    oauth = SpotifyOAuth(client_id, client_secret)
                    refreshed_info = oauth.refresh_access_token(refresh_token)
                    if refreshed_info:
                        access_token = refreshed_info.get("access_token")
                except Exception:
                    # If refresh fails, try with stored token anyway
                    pass

            # Prefer creating a fresh client via client credentials when
            # client id/secret are available. This avoids using a stale or
            # invalid saved access token which would cause immediate 401s.
            if client_id and client_secret:
                try:
                    from .oauth import SpotifyOAuth

                    oauth = SpotifyOAuth(client_id, client_secret)
                    token_info_new = oauth.client_credentials_token()
                    token = token_info_new.get("access_token")
                    sp = Spotify(access_token=token)
                    _GLOBAL_SPOTIFY = sp
                    return sp
                except Exception:
                    # fall back to saved access token if client-credentials failed
                    pass

            if access_token:
                sp = Spotify(access_token=access_token)
                _GLOBAL_SPOTIFY = sp
                return sp
    except Exception:
        # ignore and raise below
        pass

    raise SpotifyException("Global Spotify client not set and no credentials found in environment or config file")


def clear_global_spotify():
    """Clear the module-global Spotify instance (useful for tests)."""
    global _GLOBAL_SPOTIFY
    _GLOBAL_SPOTIFY = None

    def current_user_playlists(self):
        return self._request("GET", "/me/playlists")
