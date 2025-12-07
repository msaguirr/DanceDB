#!/usr/bin/env python3
"""Simple Tkinter GUI for the minimal myspotipy wrapper.

Features:
- Set access token or client credentials (creates a global Spotify client)
- Search by song name (optional artist) and list results
- Create a `Song` from a selected search result and show its details

This GUI is intentionally small and dependency-free (uses Tkinter).
"""
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
import urllib.parse
from tkinter import simpledialog
import threading
import http.server
import socketserver
import os
import json
import base64
import time
import socket

from myspotipy.client import Spotify, set_global_spotify, get_global_spotify
from myspotipy.oauth import SpotifyOAuth
from song import create_from_spotify


class SpotipyGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MySpotipy GUI")
        self.geometry("800x480")

        self._build_ui()
        # try to load saved config (tokens / creds)
        try:
            self._load_config()
        except Exception:
            pass
        # Attempt to ensure we have a Spotify client silently on startup.
        # This will (in order):
        # 1. Try to create a global client from saved access token or client creds.
        # 2. If client creds exist and a redirect URI is available, automatically
        #    open the browser and complete an Authorization Code flow in the
        #    background (no GUI prompts). Results are persisted.
        try:
            threading.Thread(target=self._first_run_onboarding, daemon=True).start()
        except Exception:
            pass
        # start background refresher thread to keep token alive
        self._stop_refresher = threading.Event()
        self._refresher_thread = threading.Thread(target=self._token_refresher_loop, daemon=True)
        self._refresher_thread.start()

    def _build_ui(self):
        frm = ttk.Frame(self, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        # Simplified UI: hide all authentication controls from the user.
        # The app will attempt to authenticate silently (from saved config or
        # environment variables) and refresh tokens in the background.
        self._config_path = os.path.join(os.path.expanduser("~"), ".myspotipy", "config.json")
        self._local_server_thread = None
        self._local_server = None
        # Note: credential management and auth helpers still exist in code but
        # are intentionally not exposed in the primary UI to keep things simple.

        # Search section
        search_frm = ttk.LabelFrame(frm, text="Search")
        search_frm.pack(fill=tk.X, pady=8)
        ttk.Label(search_frm, text="Song name:").grid(row=0, column=0, sticky=tk.W)
        self.song_var = tk.StringVar()
        song_entry = ttk.Entry(search_frm, textvariable=self.song_var, width=40)
        song_entry.grid(row=0, column=1, sticky=tk.W)
        # allow pressing Enter in the song field to start search
        song_entry.bind("<Return>", lambda e: self._search())
        ttk.Label(search_frm, text="Artist (optional):").grid(row=0, column=2, sticky=tk.W)
        self.artist_var = tk.StringVar()
        artist_entry = ttk.Entry(search_frm, textvariable=self.artist_var, width=30)
        artist_entry.grid(row=0, column=3, sticky=tk.W)
        # allow pressing Enter in the artist field to start search
        artist_entry.bind("<Return>", lambda e: self._search())
        ttk.Label(search_frm, text="Max results:").grid(row=0, column=4, sticky=tk.W)
        self.k_var = tk.IntVar(value=15)
        ttk.Spinbox(search_frm, from_=1, to=50, textvariable=self.k_var, width=6).grid(row=0, column=5, sticky=tk.W)
        ttk.Button(search_frm, text="Search", command=self._search).grid(row=0, column=6, padx=6)

        # Results and actions
        results_frm = ttk.Frame(frm)
        results_frm.pack(fill=tk.BOTH, expand=True)

        self.results_list = tk.Listbox(results_frm, height=12)
        self.results_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(results_frm, orient=tk.VERTICAL, command=self.results_list.yview)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.results_list.config(yscrollcommand=scrollbar.set)
        # when the selection changes, update cover and details
        self.results_list.bind("<<ListboxSelect>>", lambda e: self._on_result_select())

        actions = ttk.Frame(results_frm, padding=6)
        actions.pack(side=tk.RIGHT, fill=tk.Y)
        ttk.Button(actions, text="Create Song from Selected", command=self._create_song).pack(fill=tk.X, pady=4)
        ttk.Button(actions, text="Clear Results", command=lambda: self.results_list.delete(0, tk.END)).pack(fill=tk.X, pady=4)

        # Details box (with album cover)
        details_frm = ttk.LabelFrame(frm, text="Song Details")
        details_frm.pack(fill=tk.BOTH, expand=True, pady=8)
        details_inner = ttk.Frame(details_frm)
        details_inner.pack(fill=tk.BOTH, expand=True)

        # Image label on the left
        self._cover_label = ttk.Label(details_inner)
        self._cover_label.pack(side=tk.LEFT, padx=(0, 8))
        self._art_image_ref = None

        # Text details on the right
        self.details_text = tk.Text(details_inner, height=6)
        self.details_text.pack(fill=tk.BOTH, expand=True)

        # Menubar (Advanced options)
        menubar = tk.Menu(self)
        adv_menu = tk.Menu(menubar, tearoff=0)
        adv_menu.add_command(label="Re-authenticate", command=self._advanced_reauth)
        adv_menu.add_command(label="Open Logs", command=self._open_logs)
        adv_menu.add_command(label="Open Dashboard", command=self._open_dashboard)
        menubar.add_cascade(label="Advanced", menu=adv_menu)
        self.config(menu=menubar)

        # internal storage for search results
        self._search_results = []

        # GUI is intentionally minimal: no credential fields or auth buttons.
        # Routine status/info is logged to `~/.myspotipy/gui.log`.

    def _set_status(self, msg: str):
        # forward to logger for backward compatibility
        self._log(msg)

    def _log(self, msg: str):
        try:
            d = os.path.dirname(self._config_path)
            if not os.path.exists(d):
                os.makedirs(d, exist_ok=True)
            log_path = os.path.join(d, "gui.log")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")
        except Exception:
            pass
    def _open_logs(self):
        try:
            p = os.path.join(os.path.expanduser("~"), ".myspotipy", "gui.log")
            if os.path.exists(p):
                webbrowser.open(f"file://{p}")
            else:
                self._log("No GUI log found to open")
        except Exception:
            pass

    def _advanced_reauth(self):
        # Try to re-run automatic auth. Prefer environment/config creds, else prompt.
        import os

        cid = os.getenv("SPOTIFY_CLIENT_ID") or getattr(self, "_loaded_client_id", None)
        cs = os.getenv("SPOTIFY_CLIENT_SECRET") or getattr(self, "_loaded_client_secret", None)
        if not cid or not cs:
            # prompt user for credentials in an advanced flow
            cid = simpledialog.askstring("Client ID", "Enter Spotify Client ID (advanced):", parent=self)
            cs = simpledialog.askstring("Client Secret", "Enter Spotify Client Secret (advanced):", parent=self)
        if cid and cs:
            threading.Thread(target=lambda: self._start_auth_auto(cid, cs), daemon=True).start()
        else:
            self._log("Re-authentication canceled or no credentials provided")

    def _first_run_onboarding(self):
        """Perform silent onboarding on first run.

        Behavior:
        - If a global Spotify client already exists, do nothing.
        - Try to create a client via `get_global_spotify(create_if_missing=True)`
          which will use env vars or saved config (client credentials or access token).
        - If that yields a client, we're done. If client credentials exist and
          a redirect URI is available in config or env, start an automatic
          Authorization Code flow in the background so we can obtain a
          refresh token for long-lived sessions.
        """
        try:
            from myspotipy.client import get_global_spotify

            try:
                sp = get_global_spotify(create_if_missing=True)
                if sp:
                    self._log("Global Spotify client available (silent)")
                    return
            except Exception:
                # fall through to attempts below
                pass

            # Inspect saved/loaded config and environment for credentials
            import os

            client_id = getattr(self, "_loaded_client_id", None) or os.getenv("SPOTIFY_CLIENT_ID")
            client_secret = getattr(self, "_loaded_client_secret", None) or os.getenv("SPOTIFY_CLIENT_SECRET")
            redirect_uri = getattr(self, "_loaded_redirect_uri", None) or os.getenv("SPOTIFY_REDIRECT_URI")

            # If we have client credentials, ensure a basic client exists (client credentials flow)
            if client_id and client_secret:
                try:
                    from myspotipy.oauth import SpotifyOAuth

                    oauth = SpotifyOAuth(client_id, client_secret)
                    info = oauth.client_credentials_token()
                    token = info.get("access_token")
                    if token:
                        from myspotipy.client import set_global_spotify

                        set_global_spotify(Spotify(access_token=token))
                        self._log("Obtained client-credentials token silently")
                except Exception as e:
                    self._log(f"Silent client-credentials flow failed: {e}")

                # If redirect URI exists, attempt a full Authorization Code flow
                # to obtain a refresh token for long-lived sessions. This will
                # open the browser but will not display any GUI prompts.
                if redirect_uri:
                    try:
                        threading.Thread(target=lambda: self._start_auth_auto(client_id, client_secret, redirect_uri), daemon=True).start()
                        self._log("Started background Authorization Code onboarding (check browser)")
                    except Exception as e:
                        self._log(f"Background authorization failed to start: {e}")
            else:
                self._log("No client credentials found for silent onboarding")
        except Exception as e:
            self._log(f"Onboarding error: {e}")
    def _set_token(self):
        token = self.token_var.get().strip()
        if not token:
            self._set_status("No access token provided")
            return
        sp = Spotify(access_token=token)
        set_global_spotify(sp)
        self._set_status("Access token set")
        # persist token (base64 encode for minimal obfuscation)
        try:
            self._save_config({"access_token": base64.b64encode(token.encode()).decode()})
        except Exception:
            pass

    def _set_client_credentials(self):
        cid = self.client_id_var.get().strip()
        cs = self.client_secret_var.get().strip()
        if not cid or not cs:
            self._set_status("Missing client id or client secret")
            return
        try:
            oauth = SpotifyOAuth(cid, cs)
            token_info = oauth.client_credentials_token()
            token = token_info.get("access_token")
            sp = Spotify(access_token=token)
            set_global_spotify(sp)
            self._set_status("Client credentials set and token obtained")
        except Exception as e:
            self._log(f"Failed to create client: {e}")
            return
        # persist client id/secret (base64-encoded)
        try:
            self._save_config({"client_id": base64.b64encode(cid.encode()).decode(), "client_secret": base64.b64encode(cs.encode()).decode(), "expires_at": token_info.get("expires_at")})
        except Exception:
            pass

    def _start_auth(self):
        cid = self.client_id_var.get().strip()
        redirect = self.redirect_var.get().strip()
        scope = self.scope_var.get().strip() or None
        if not cid or not redirect:
            self._set_status("Missing client id or redirect URI for authorization")
            return
        # Build authorize URL
        try:
            oauth = SpotifyOAuth(cid, client_secret="", redirect_uri=redirect, scope=scope)
            auth_url = oauth.get_authorize_url()
            webbrowser.open(auth_url)
            self._set_status("Browser opened for authorization")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to build authorize URL: {e}")

    def _open_dashboard(self):
        """Open the Spotify Developer Dashboard in the default browser."""
        webbrowser.open("https://developer.spotify.com/dashboard/applications")

    def _validate_credentials(self):
        """Quick validation: check client id/secret by obtaining a client-credentials token,
        and check redirect URI format and port availability.
        """
        cid = self.client_id_var.get().strip()
        cs = self.client_secret_var.get().strip()
        redirect = self.redirect_var.get().strip()

        if not cid or not cs:
            self._set_status("Missing client id or client secret for validation")
            return

        # validate client credentials by requesting a token
        try:
            oauth = SpotifyOAuth(cid, cs)
            info = oauth.client_credentials_token()
            expires_in = info.get("expires_in")
            token = info.get("access_token")
            msg = f"Client credentials OK. Access token obtained (expires in {expires_in}s)."
        except Exception as e:
            self._log(f"Client credentials validation failed: {e}")
            return

        # validate redirect URI
        try:
            parsed = urllib.parse.urlparse(redirect)
            if parsed.scheme not in ("http", "https"):
                msg += "\nRedirect URI must be http or https."
            elif parsed.hostname not in ("localhost", "127.0.0.1"):
                msg += "\nNote: Auto Auth works best with localhost redirect URIs."
            # check port availability if specified
            if parsed.port:
                port = parsed.port
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    try:
                        s.bind((parsed.hostname, port))
                        s.listen(1)
                        s.close()
                    except Exception:
                        msg += f"\nWarning: port {port} appears unavailable on localhost. Auto Auth may fail."
        except Exception:
            msg += "\nRedirect URI appears malformed."

        # show success message silently in status bar
        self._set_status(msg)

    def _start_auth_auto(self, cid=None, cs=None, redirect=None, scope=None):
        """Start a temporary local HTTP server to receive the authorization redirect.

        This opens the browser to the authorize URL and waits for the redirect to
        be delivered to the configured redirect URI (must be a localhost URL).
        """
        # Allow caller to pass credentials; otherwise fall back to loaded config or env.
        import os

        cid = cid or getattr(self, "_loaded_client_id", None) or os.getenv("SPOTIFY_CLIENT_ID")
        cs = cs or getattr(self, "_loaded_client_secret", None) or os.getenv("SPOTIFY_CLIENT_SECRET")
        redirect = redirect or getattr(self, "_loaded_redirect_uri", None) or os.getenv("SPOTIFY_REDIRECT_URI") or "http://localhost:8888/callback"
        scope = scope or None
        if not cid or not redirect:
            self._set_status("Missing client id or redirect URI for automatic authorization")
            return

        parsed = urllib.parse.urlparse(redirect)
        if parsed.scheme != "http" or parsed.hostname not in ("localhost", "127.0.0.1"):
            messagebox.showwarning("Redirect URI", "Auto Auth requires a localhost HTTP redirect URI (e.g. http://localhost:8888/callback).")
            return

        # if redirect has no port, pick a free ephemeral port and update redirect
        parsed = urllib.parse.urlparse(redirect)
        host = parsed.hostname
        if parsed.port:
            port = parsed.port
            redirect_used = redirect
        else:
            # find a free port
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((host, 0))
                port = s.getsockname()[1]
            redirect_used = f"{parsed.scheme}://{host}:{port}{parsed.path}"
            self._set_status(f"Using redirect URI {redirect_used}")

        try:
            oauth = SpotifyOAuth(cid, cs, redirect_uri=redirect_used, scope=scope)
            auth_url = oauth.get_authorize_url()
        except Exception as e:
            self._log(f"Failed to build authorize URL: {e}")
            return

        # Start local HTTP server in background thread
        # host and port set above

        parent = self

        class _Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                qs = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(qs)
                code_list = params.get("code")
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                if code_list:
                    code = code_list[0]
                    try:
                        oauth_local = SpotifyOAuth(cid, cs, redirect_uri=redirect_used, scope=scope)
                        token_info = oauth_local.exchange_code(code)
                        token = token_info.get("access_token")
                        sp_local = Spotify(access_token=token)
                        set_global_spotify(sp_local)
                        # persist token_info and client creds
                        try:
                            data = {
                                "access_token": base64.b64encode(token.encode()).decode(),
                                "client_id": base64.b64encode(cid.encode()).decode(),
                                "client_secret": base64.b64encode(cs.encode()).decode(),
                            }
                            if token_info.get("refresh_token"):
                                data["refresh_token"] = base64.b64encode(token_info.get("refresh_token").encode()).decode()
                            if token_info.get("expires_at"):
                                data["expires_at"] = token_info.get("expires_at")
                            # ensure config dir exists
                            try:
                                parent._save_config(data)
                            except Exception:
                                pass
                        except Exception:
                            pass
                        self.wfile.write(b"<html><body><h2>Authentication successful. You can close this window.</h2></body></html>")
                    except Exception as e:
                        self.wfile.write(b"<html><body><h2>Authentication failed.</h2></body></html>")
                    # shutdown server after handling
                    def _shutdown():
                        try:
                            parent._local_server.shutdown()
                        except Exception:
                            pass
                    threading.Thread(target=_shutdown, daemon=True).start()
                else:
                    self.wfile.write(b"<html><body><h2>No code found in redirect.</h2></body></html>")

            def log_message(self, format, *args):
                return

        try:
            httpd = socketserver.TCPServer((host, port), _Handler)
        except Exception as e:
            self._log(f"Failed to start local server on {host}:{port}: {e}")
            return

        self._local_server = httpd

        def _serve():
            try:
                httpd.serve_forever()
            except Exception:
                pass

        t = threading.Thread(target=_serve, daemon=True)
        t.start()
        self._local_server_thread = t

        # Open browser for auth
        webbrowser.open(auth_url)
        self._set_status("Auth started; waiting for redirect...")

    def _complete_auth(self):
        # Extract code from pasted redirect URL or accept raw code
        pasted = self.redirect_result_var.get().strip()
        if not pasted:
            self._log("No input provided for authorization completion")
            return
        # determine if it's a full URL
        code = None
        try:
            if pasted.startswith("http"):
                parsed = urllib.parse.urlparse(pasted)
                qs = urllib.parse.parse_qs(parsed.query)
                code_list = qs.get("code")
                if code_list:
                    code = code_list[0]
            else:
                code = pasted
        except Exception:
            code = pasted

        if not code:
            messagebox.showerror("No code", "Could not extract authorization code from input.")
            return

        cid = self.client_id_var.get().strip()
        cs = self.client_secret_var.get().strip()
        redirect = self.redirect_var.get().strip()
        if not cid or not cs or not redirect:
            self._set_status("Missing client id, secret, or redirect for completing auth")
            return

        try:
            oauth = SpotifyOAuth(cid, cs, redirect_uri=redirect)
            token_info = oauth.exchange_code(code)
            token = token_info.get("access_token")
            sp = Spotify(access_token=token)
            set_global_spotify(sp)
            self._set_status("Authenticated via authorization code flow")
            # persist token and client info
            try:
                data = {"access_token": base64.b64encode(token.encode()).decode(), "client_id": base64.b64encode(cid.encode()).decode(), "client_secret": base64.b64encode(cs.encode()).decode()}
                if token_info.get("refresh_token"):
                    data["refresh_token"] = base64.b64encode(token_info.get("refresh_token").encode()).decode()
                if token_info.get("expires_at"):
                    data["expires_at"] = token_info.get("expires_at")
                if redirect:
                    data["redirect_uri"] = redirect
                self._save_config(data)
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("Auth error", f"Failed to exchange code: {e}")

    def _search(self):
        query = self.song_var.get().strip()
        artist = self.artist_var.get().strip() or None
        k = int(self.k_var.get() or 5)
        if not query:
            self._set_status("Enter a song name to search for")
            return

        try:
            sp = get_global_spotify(create_if_missing=False)
        except Exception:
            sp = None

        if sp is None:
            # attempt to create global spotify client from env vars silently
            try:
                sp = get_global_spotify(create_if_missing=True)
            except Exception:
                sp = None
        if sp is None:
            self._set_status("No Spotify client available (set credentials or token)")
            return

        try:
            results = sp.search_tracks(query, artist=artist, k=k)
        except Exception as e:
            messagebox.showerror("Search error", f"Search failed: {e}")
            return

        self._search_results = results
        self.results_list.delete(0, tk.END)
        for r in results:
            display = f"{r.get('name')} — {', '.join(r.get('artists', []))}"
            self.results_list.insert(tk.END, display)

    def _create_song(self):
        sel = self.results_list.curselection()
        if not sel:
            messagebox.showwarning("No selection", "Select a search result first.")
            return
        idx = sel[0]
        track_obj = self._search_results[idx]
        try:
            song = create_from_spotify(track_obj)
            self.details_text.delete("1.0", tk.END)
            self.details_text.insert(tk.END, repr(song))
        except Exception as e:
            messagebox.showerror("Create error", f"Failed to create Song: {e}")

    def _on_result_select(self):
        """Update details area and album cover when a result is selected."""
        sel = self.results_list.curselection()
        if not sel:
            # clear image and details
            try:
                self._cover_label.configure(image="", text="")
                self._art_image_ref = None
            except Exception:
                pass
            return
        idx = sel[0]
        track_obj = self._search_results[idx]
        # get raw track data
        raw = track_obj.get("raw", track_obj) if isinstance(track_obj, dict) else {}
        # show textual details immediately
        album_name = (raw.get("album") or {}).get("name") if raw.get("album") else None
        artists = ", ".join([a.get("name") for a in raw.get("artists", [])]) if raw.get("artists") else ""
        txt = f"Title: {raw.get('name', '')}\nArtists: {artists}\nAlbum: {album_name or ''}\n"
        self.details_text.delete("1.0", tk.END)
        self.details_text.insert(tk.END, txt)

        # attempt to fetch the album image in background
        images = []
        try:
            images = (raw.get("album", {}) or {}).get("images", [])
        except Exception:
            images = []

        if not images:
            # clear image
            try:
                self._cover_label.configure(image="", text=album_name or "No cover")
                self._art_image_ref = None
            except Exception:
                pass
            return

        url = images[0].get("url") if images and images[0].get("url") else None
        if not url:
            try:
                self._cover_label.configure(image="", text=album_name or "No cover")
                self._art_image_ref = None
            except Exception:
                pass
            return

        def _fetch_and_show(u):
            try:
                import requests
                from io import BytesIO
                try:
                    from PIL import Image, ImageTk
                    pil_ok = True
                except Exception:
                    pil_ok = False

                r = requests.get(u, timeout=10)
                r.raise_for_status()
                data = r.content
                if pil_ok:
                    img = Image.open(BytesIO(data))
                    img.thumbnail((160, 160))
                    photo = ImageTk.PhotoImage(img)

                    def _update():
                        try:
                            self._cover_label.configure(image=photo, text="")
                            self._art_image_ref = photo
                        except Exception:
                            pass

                    self.after(0, _update)
                else:
                    # no PIL: don't attempt to render binary image; just show album name
                    def _update_no_pil():
                        try:
                            self._cover_label.configure(image="", text=album_name or "Cover")
                            self._art_image_ref = None
                        except Exception:
                            pass

                    self.after(0, _update_no_pil)
            except Exception:
                try:
                    self._cover_label.configure(image="", text=album_name or "No cover")
                except Exception:
                    pass

        threading.Thread(target=lambda: _fetch_and_show(url), daemon=True).start()

    # --- config persistence helpers ---
    def _ensure_config_dir(self):
        d = os.path.dirname(self._config_path)
        if not os.path.exists(d):
            os.makedirs(d, exist_ok=True)

    def _save_config(self, data: dict):
        """Merge and save provided data into config file. Values are stored as-is (some are base64-encoded).

        This writes a JSON file at `~/.myspotipy/config.json`.
        """
        try:
            self._ensure_config_dir()
            existing = {}
            if os.path.exists(self._config_path):
                with open(self._config_path, "r") as f:
                    try:
                        existing = json.load(f)
                    except Exception:
                        existing = {}
            existing.update(data)
            with open(self._config_path, "w") as f:
                json.dump(existing, f)
        except Exception:
            raise

    def _load_config(self):
        """Load config (if present) and set GUI fields and global client when possible.

        Decodes base64-encoded tokens where applicable and refreshes tokens if expired
        and refresh token + client credentials are available.
        """
        if not os.path.exists(self._config_path):
            return
        with open(self._config_path, "r") as f:
            cfg = json.load(f)

        # decode fields if base64 encoded
        def _maybe_b64(s):
            if not s:
                return s
            try:
                # assume b64 string if it contains non-whitespace and decodable
                return base64.b64decode(s).decode()
            except Exception:
                return s

        access_token = _maybe_b64(cfg.get("access_token"))
        refresh_token = _maybe_b64(cfg.get("refresh_token"))
        client_id = _maybe_b64(cfg.get("client_id"))
        client_secret = _maybe_b64(cfg.get("client_secret"))
        redirect_uri = cfg.get("redirect_uri") or self.redirect_var.get()
        expires_at = cfg.get("expires_at")

        # populate UI fields
        if client_id:
            self.client_id_var.set(client_id)
        if client_secret:
            self.client_secret_var.set(client_secret)
        if redirect_uri:
            self.redirect_var.set(redirect_uri)

        # if token present and not expired, set global client
        now = int(time.time())
        token_to_use = None
        if access_token and expires_at and isinstance(expires_at, (int, float)) and now < int(expires_at):
            token_to_use = access_token
        elif access_token and not expires_at:
            token_to_use = access_token
        elif refresh_token and client_id and client_secret:
            # try refresh
            try:
                oauth = SpotifyOAuth(client_id, client_secret, redirect_uri=redirect_uri)
                new = oauth.refresh_access_token(refresh_token)
                token_to_use = new.get("access_token")
                # persist refreshed token
                saved = {"access_token": base64.b64encode(token_to_use.encode()).decode(), "expires_at": new.get("expires_at")}
                if new.get("refresh_token"):
                    saved["refresh_token"] = base64.b64encode(new.get("refresh_token").encode()).decode()
                self._save_config(saved)
            except Exception:
                token_to_use = None

        if token_to_use:
            sp = Spotify(access_token=token_to_use)
            set_global_spotify(sp)
            self.token_var.set(token_to_use)
            # store loaded config values for refresher
            self._loaded_client_id = client_id
            self._loaded_client_secret = client_secret
            self._loaded_refresh_token = refresh_token
            try:
                self._loaded_expires_at = int(expires_at) if expires_at else None
            except Exception:
                self._loaded_expires_at = None
        else:
            self._loaded_client_id = client_id
            self._loaded_client_secret = client_secret
            self._loaded_refresh_token = refresh_token
            self._loaded_expires_at = expires_at

    def _token_refresher_loop(self):
        """Background loop that refreshes or renews tokens before expiry.

        Behavior:
        - If a refresh token is available, use Authorization Code refresh flow.
        - Otherwise, if client id/secret present, use Client Credentials to obtain a new token.
        - Persist new tokens via `_save_config`.
        """
        while not getattr(self, "_stop_refresher", threading.Event()).is_set():
            try:
                expires_at = getattr(self, "_loaded_expires_at", None)
                now = int(time.time())
                # default check interval
                wait = 30
                if expires_at and isinstance(expires_at, int):
                    # refresh 60s before expiry
                    if now >= expires_at - 60:
                        # perform refresh
                        refreshed = False
                        try:
                            if getattr(self, "_loaded_refresh_token", None) and getattr(self, "_loaded_client_id", None) and getattr(self, "_loaded_client_secret", None):
                                oauth = SpotifyOAuth(self._loaded_client_id, self._loaded_client_secret, redirect_uri=self.redirect_var.get())
                                new = oauth.refresh_access_token(self._loaded_refresh_token)
                                new_token = new.get("access_token")
                                new_expires_at = new.get("expires_at") or int(time.time()) + new.get("expires_in", 3600)
                                if new_token:
                                    sp = Spotify(access_token=new_token)
                                    set_global_spotify(sp)
                                    # persist
                                    saved = {"access_token": base64.b64encode(new_token.encode()).decode(), "expires_at": new_expires_at}
                                    if new.get("refresh_token"):
                                        saved["refresh_token"] = base64.b64encode(new.get("refresh_token").encode()).decode()
                                    self._save_config(saved)
                                    self._loaded_expires_at = int(new_expires_at)
                                    self._loaded_refresh_token = new.get("refresh_token") or self._loaded_refresh_token
                                    refreshed = True
                        except Exception:
                            refreshed = False

                        if not refreshed and getattr(self, "_loaded_client_id", None) and getattr(self, "_loaded_client_secret", None):
                            # fall back to client credentials
                            try:
                                oauth = SpotifyOAuth(self._loaded_client_id, self._loaded_client_secret)
                                info = oauth.client_credentials_token()
                                token = info.get("access_token")
                                expires_at_new = int(time.time()) + info.get("expires_in", 3600)
                                if token:
                                    sp = Spotify(access_token=token)
                                    set_global_spotify(sp)
                                    self._save_config({"access_token": base64.b64encode(token.encode()).decode(), "expires_at": expires_at_new})
                                    self._loaded_expires_at = expires_at_new
                            except Exception:
                                pass
                        # after attempting refresh, wait a bit
                        wait = 30
                    else:
                        # sleep until shortly before expiry or default interval
                        wait = max(10, min(300, (expires_at - now) // 2))
                else:
                    # no expiry known; if client credentials available, try to obtain a token periodically
                    if getattr(self, "_loaded_client_id", None) and getattr(self, "_loaded_client_secret", None):
                        try:
                            oauth = SpotifyOAuth(self._loaded_client_id, self._loaded_client_secret)
                            info = oauth.client_credentials_token()
                            token = info.get("access_token")
                            expires_at_new = int(time.time()) + info.get("expires_in", 3600)
                            if token:
                                sp = Spotify(access_token=token)
                                set_global_spotify(sp)
                                self._save_config({"access_token": base64.b64encode(token.encode()).decode(), "expires_at": expires_at_new})
                                self._loaded_expires_at = expires_at_new
                                wait = max(60, info.get("expires_in", 3600) - 60)
                        except Exception:
                            wait = 60

                # wait but allow fast exit
                for _ in range(int(wait)):
                    if getattr(self, "_stop_refresher", threading.Event()).is_set():
                        break
                    time.sleep(1)
            except Exception:
                time.sleep(30)

    def destroy(self):
        try:
            self._stop_refresher.set()
        except Exception:
            pass
        try:
            if self._local_server:
                try:
                    self._local_server.shutdown()
                except Exception:
                    pass
        except Exception:
            pass
        super().destroy()


def main():
    app = SpotipyGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
