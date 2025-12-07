import base64
import time
import base64
import time
import urllib.parse
import requests


class SpotifyOAuth:
    """Minimal OAuth / token helpers for Spotify Web API.

    - `client_credentials_token()` obtains a client-credentials token.
    - `get_authorize_url()` builds an authorize URL for the Authorization Code flow.
    - `exchange_code()` exchanges an authorization code for tokens.
    - `refresh_access_token()` refreshes an access token.
    """

    TOKEN_URL = "https://accounts.spotify.com/api/token"
    AUTHORIZE_URL = "https://accounts.spotify.com/authorize"

    def __init__(self, client_id, client_secret, redirect_uri=None, scope=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scope = scope

    def _basic_auth_header(self):
        creds = f"{self.client_id}:{self.client_secret}".encode("utf-8")
        return {"Authorization": "Basic " + base64.b64encode(creds).decode("utf-8")}

    def client_credentials_token(self):
        data = {"grant_type": "client_credentials"}
        headers = self._basic_auth_header()
        r = requests.post(self.TOKEN_URL, data=data, headers=headers, timeout=10)
        r.raise_for_status()
        token_data = r.json()
        token_data["expires_at"] = int(time.time()) + token_data.get("expires_in", 3600)
        return token_data

    def get_authorize_url(self, state=None, show_dialog=False):
        params = {"client_id": self.client_id, "response_type": "code"}
        if self.redirect_uri:
            params["redirect_uri"] = self.redirect_uri
        if self.scope:
            params["scope"] = self.scope
        if state:
            params["state"] = state
        if show_dialog:
            params["show_dialog"] = "true"
        return self.AUTHORIZE_URL + "?" + urllib.parse.urlencode(params)

    def exchange_code(self, code):
        data = {"grant_type": "authorization_code", "code": code}
        if self.redirect_uri:
            data["redirect_uri"] = self.redirect_uri
        headers = self._basic_auth_header()
        r = requests.post(self.TOKEN_URL, data=data, headers=headers, timeout=10)
        r.raise_for_status()
        token_data = r.json()
        token_data["expires_at"] = int(time.time()) + token_data.get("expires_in", 3600)
        return token_data

    def refresh_access_token(self, refresh_token):
        data = {"grant_type": "refresh_token", "refresh_token": refresh_token}
        headers = self._basic_auth_header()
        r = requests.post(self.TOKEN_URL, data=data, headers=headers, timeout=10)
        r.raise_for_status()
        token_data = r.json()
        token_data["expires_at"] = int(time.time()) + token_data.get("expires_in", 3600)
        return token_data
        return token_data
