#!/usr/bin/env python3
"""Dance manager GUI that embeds a Spotipy search pane.

Left: list of dances (from CSV). Middle: dance details and songs. Right:
search pane (search tracks, view results, add selected song to chosen dance).

This keeps the Spotipy search logic local and reuses `create_from_spotify`
to build `Song` objects to attach to dances stored in CSV.
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
import io
import threading
import time
from typing import Optional
import traceback
# CSV storage
from csv_writer import CSVDatabase
# Spotify client helpers
from myspotipy.client import get_global_spotify, set_global_spotify, clear_global_spotify
# Song creation
from song import create_from_spotify
# optional Pillow for album art rendering
try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None


DEFAULT_CSV = os.path.join(os.path.expanduser("~"), "dances.csv")
DEFAULT_FIELDS = ["name", "level", "choreographers", "release_date", "songs", "notes", "copperknob_id"]


class SpotipySearchFrame(ttk.LabelFrame):
    def __init__(self, parent):
        super().__init__(parent, text="Search")
        self.song_var = tk.StringVar()
        self.artist_var = tk.StringVar()
        self.k_var = tk.IntVar(value=15)

        ttk.Label(self, text="Song:").grid(row=0, column=0, sticky=tk.W)
        self.song_entry = ttk.Entry(self, textvariable=self.song_var, width=30)
        self.song_entry.grid(row=0, column=1, sticky=tk.W)
        self.song_entry.bind("<Return>", lambda e: self._search())

        ttk.Label(self, text="Artist:").grid(row=1, column=0, sticky=tk.W)
        self.artist_entry = ttk.Entry(self, textvariable=self.artist_var, width=30)
        self.artist_entry.grid(row=1, column=1, sticky=tk.W)
        self.artist_entry.bind("<Return>", lambda e: self._search())

        ttk.Label(self, text="Max:").grid(row=0, column=2, sticky=tk.W)
        ttk.Spinbox(self, from_=1, to=50, textvariable=self.k_var, width=5).grid(row=0, column=3, sticky=tk.W)

        ttk.Button(self, text="Search", command=self._search).grid(row=0, column=4, padx=6)

        self.results_list = tk.Listbox(self, height=10, exportselection=False)
        self.results_list.grid(row=2, column=0, columnspan=5, sticky="nsew")
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._search_results = []
        self._preview_photo = None
        self.results_list.bind("<<ListboxSelect>>", lambda e: self._on_result_select())

        # preview area below results
        self._preview_text = tk.Text(self, height=6, width=40, wrap='word')
        self._preview_text.grid(row=3, column=0, columnspan=5, sticky='nsew')
        self._preview_text.config(state='disabled')

    def _search(self):
        q = self.song_var.get().strip()
        if not q:
            return
        artist = self.artist_var.get().strip() or None
        k = int(self.k_var.get() or 15)
        try:
            sp = get_global_spotify(create_if_missing=True)
        except Exception:
            sp = None
        if sp is None:
            messagebox.showerror("No Spotify client", "No Spotify client available. Set SPOTIFY_CLIENT_ID/SECRET or login.")
            return
        try:
            results = sp.search_tracks(q, artist=artist, k=k)
        except Exception as e:
            messagebox.showerror("Search error", f"Search failed: {e}")
            return
        self._search_results = results
        self.results_list.delete(0, tk.END)
        for r in results:
            display = f"{r.get('name')} — {', '.join(r.get('artists', []))}"
            self.results_list.insert(tk.END, display)

    def _on_result_select(self):
        sel = self.results_list.curselection()
        if not sel:
            try:
                self._preview_text.config(state='normal')
                self._preview_text.delete('1.0', tk.END)
                self._preview_text.config(state='disabled')
            except Exception:
                pass
            return
        idx = sel[0]
        if idx < 0 or idx >= len(self._search_results):
            return
        track = self._search_results[idx]
        title = track.get('name') or ''
        artists = ', '.join(track.get('artists') or [])
        lines = [f"Name: {title}", f"Artist: {artists}"]
        try:
            raw = track.get('raw') or {}
            album = raw.get('album', {})
            images = album.get('images', [])
            album_url = images[0].get('url') if images else None
        except Exception:
            album_url = None
        try:
            self._preview_text.config(state='normal')
            self._preview_text.delete('1.0', tk.END)
            self._preview_text.insert(tk.END, '\n'.join(lines))
            self._preview_text.config(state='disabled')
        except Exception:
            pass
        if album_url and Image and ImageTk:
            try:
                import requests
                resp = requests.get(album_url, timeout=6)
                if resp.ok:
                    img = Image.open(io.BytesIO(resp.content))
                    img.thumbnail((160, 160))
                    self._preview_photo = ImageTk.PhotoImage(img)
                    # show in preview text by clearing and showing text + no image widget (keep simple)
                    return
            except Exception:
                pass

    def get_selected_track(self):
        sel = self.results_list.curselection()
        if not sel:
            return None
        idx = sel[0]
        if idx < 0 or idx >= len(self._search_results):
            return None
        return self._search_results[idx]


class DanceManagerApp(tk.Tk):
    def __init__(self, csv_path=DEFAULT_CSV):
        super().__init__()
        self.title("Dance Manager")
        self.geometry("1000x600")

        self.csv_path = csv_path
        self.db = CSVDatabase(self.csv_path, DEFAULT_FIELDS)

        self._build_ui()
        self._load_dances()

    def _build_ui(self):
        main = ttk.Frame(self, padding=8)
        main.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(main, width=240)
        left.pack(side=tk.LEFT, fill=tk.Y)
        top_left = ttk.Frame(left)
        top_left.pack(fill=tk.X)
        ttk.Label(top_left, text="Dances").pack(side=tk.LEFT, anchor=tk.W)
        # auth controls
        self._auth_status = tk.StringVar(value='Not signed in')
        self._login_btn = ttk.Button(top_left, text='Login', width=8, command=self._authenticate_spotify)
        self._login_btn.pack(side=tk.RIGHT, padx=(4,0))
        self._logout_btn = ttk.Button(top_left, text='Logout', width=8, command=self._logout_spotify)
        self._logout_btn.pack(side=tk.RIGHT)
        ttk.Label(left, textvariable=self._auth_status).pack(anchor=tk.W)
        self.dance_list = tk.Listbox(left, width=30, exportselection=False)
        self.dance_list.pack(fill=tk.Y, expand=True)
        self.dance_list.bind("<<ListboxSelect>>", lambda e: self._on_dance_select())

        btns = ttk.Frame(left)
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="New", command=self._new_dance).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(btns, text="Edit", command=self._edit_dance).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(btns, text="Delete", command=self._delete_dance).pack(side=tk.LEFT, fill=tk.X)
        
        # Dance info display (level and notes)
        info_frame = ttk.LabelFrame(left, text="Dance Info", padding=5)
        info_frame.pack(fill=tk.BOTH, expand=False, pady=(5,0))
        self._dance_info_text = tk.Text(info_frame, height=4, wrap='word', state='disabled')
        self._dance_info_text.pack(fill=tk.BOTH, expand=True)

        # center: dance details and songs
        center = ttk.Frame(main)
        center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Label(center, text="Songs in Dance").pack(anchor=tk.W)
        self.songs_list = tk.Listbox(center, exportselection=False)
        self.songs_list.pack(fill=tk.BOTH, expand=True)
        # show details for the selected song in the dance
        self.songs_list.bind("<<ListboxSelect>>", lambda e: self._on_song_select())
        song_btns = ttk.Frame(center)
        song_btns.pack(fill=tk.X)
        ttk.Button(song_btns, text="Remove Song", command=self._remove_song).pack(side=tk.LEFT)

        details_frame = ttk.LabelFrame(center, text="Song Details")
        details_frame.pack(fill=tk.BOTH, expand=False, pady=(6, 0))
        # left: album art, right: details text
        art_and_text = ttk.Frame(details_frame)
        art_and_text.pack(fill=tk.BOTH, expand=True)
        self._album_art_label = ttk.Label(art_and_text)
        self._album_art_label.pack(side=tk.LEFT, padx=(6, 8), pady=6)
        self._album_photo = None
        self._song_details = tk.Text(art_and_text, height=6, wrap='word')
        self._song_details.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._song_details.config(state='disabled')
        # fetch and edit BPM buttons
        bpmbtns = ttk.Frame(details_frame)
        bpmbtns.pack(fill=tk.X, padx=6, pady=(0,6))
        ttk.Button(bpmbtns, text="Fetch BPM", command=self._fetch_bpm_for_selected_song).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(bpmbtns, text="Edit BPM", command=self._edit_bpm_for_selected_song).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6,0))
        ttk.Button(bpmbtns, text="Open in Spotify", command=self._open_in_spotify).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6,0))
        ttk.Button(bpmbtns, text="Remove from Dance", command=self._remove_selected_song_from_dance).pack(side=tk.LEFT, fill=tk.X, padx=(6,0))

        # right: search frame (hidden by default). It is shown only when adding a song.
        self.right_frame = ttk.Frame(main, width=400)
        self.search_frame = SpotipySearchFrame(self.right_frame)
        # close button for the search pane
        self._close_search_btn = ttk.Button(self.right_frame, text='X', width=3, command=self._hide_search_panel)
        # Add button (created but not packed until panel shown)
        self._add_selected_btn = ttk.Button(self.right_frame, text="Add Selected Song to Dance", command=self._add_selected_song_to_dance)
        # add 'Add Song...' control in the center controls to open the search pane
        ttk.Button(song_btns, text="Add Song...", command=self._show_search_panel).pack(side=tk.LEFT, padx=(6,0))

    def _load_dances(self):
        rows = self.db._read_all_rows()
        self._dances = rows
        self.dance_list.delete(0, tk.END)
        for r in rows:
            # Build display string with dance info
            name = r.get('name') or 'Untitled'
            level = r.get('level') or ''
            
            # Count songs
            try:
                songs = json.loads(r.get('songs') or '[]')
                song_count = len(songs) if isinstance(songs, list) else 0
            except Exception:
                song_count = 0
            
            # Format: "Dance Name [Level] (X songs)"
            display = name
            if level:
                display += f" [{level}]"
            if song_count > 0:
                display += f" ({song_count} song{'s' if song_count != 1 else ''})"
            
            self.dance_list.insert(tk.END, display)
        # update auth status (non-blocking)
        try:
            self.after(10, self._update_auth_status)
        except Exception:
            pass

    def _update_auth_status(self):
        try:
            from myspotipy.client import get_global_spotify
            sp = None
            try:
                sp = get_global_spotify(create_if_missing=False)
            except Exception:
                sp = None
            if sp is not None:
                self._auth_status.set('Signed in')
            else:
                self._auth_status.set('Not signed in')
        except Exception:
            try:
                self._auth_status.set('Not signed in')
            except Exception:
                pass

    def _reload_and_restore_dance(self, idx: int):
        """Reload dances and restore selection to idx (if valid), then refresh songs list."""
        self._load_dances()
        rows = self.db._read_all_rows()
        if idx is None:
            return
        if 0 <= idx < len(rows):
            try:
                self.dance_list.selection_clear(0, tk.END)
                self.dance_list.selection_set(idx)
                self.dance_list.activate(idx)
                self.dance_list.see(idx)
                self._on_dance_select()
            except Exception:
                pass

    def _show_search_panel(self):
        # open the search pane on the right and keep current dance selection
        sel = self.dance_list.curselection()
        if not sel:
            messagebox.showwarning("Select a dance", "Select a dance before adding a song.")
            return
        # pack the right frame and its contents if not already visible
        try:
            if not getattr(self, '_search_visible', False):
                # save current geometry so we can restore it later
                try:
                    self.update_idletasks()
                    self._saved_geometry = self.geometry()
                    w = self.winfo_width()
                    h = self.winfo_height()
                except Exception:
                    self._saved_geometry = None
                    w = None
                    h = None
                self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
                # the close button at top-right
                try:
                    self._close_search_btn.pack(side=tk.TOP, anchor=tk.E, padx=4, pady=4)
                except Exception:
                    pass
                self.search_frame.pack(fill=tk.BOTH, expand=True)
                self._add_selected_btn.pack(fill=tk.X)
                self._search_visible = True
                # resize window wider to accommodate search pane if we could read sizes
                try:
                    if w and h:
                        # add about 420 px for the search pane
                        self.geometry(f"{w+420}x{h}")
                except Exception:
                    pass
            # focus the song entry so user can type immediately
            try:
                self.search_frame.song_entry.focus_set()
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("Show search failed", f"Failed to open search pane: {e}")

    def _authenticate_spotify(self):
        # Device flow login - user just enters a code on Spotify website
        try:
            from myspotipy.client import set_global_spotify, Spotify as SpotifyClient
            import webbrowser, base64, requests, json

            # try to obtain client id/secret from env or config
            cid = os.getenv('SPOTIFY_CLIENT_ID')
            cs = os.getenv('SPOTIFY_CLIENT_SECRET')
            cfg_path = os.path.join(os.path.expanduser('~'), '.myspotipy', 'config.json')
            
            if (not cid or not cs) and os.path.exists(cfg_path):
                try:
                    with open(cfg_path, 'r', encoding='utf-8') as f:
                        cfg = json.load(f)
                    def _maybe_b64(s):
                        if not s:
                            return s
                        try:
                            return base64.b64decode(s).decode()
                        except Exception:
                            return s
                    cid = cid or _maybe_b64(cfg.get('client_id'))
                    cs = cs or _maybe_b64(cfg.get('client_secret'))
                except Exception:
                    pass

            # if still missing, prompt the user
            if not cid:
                cid = simpledialog.askstring(
                    'Spotify Client ID',
                    'Enter your Spotify Client ID\n'
                    '(from developer.spotify.com/dashboard)\n\n'
                    'Copy and paste directly - do NOT type it manually:\n\n'
                    'Hint: It should be ~32 chars long'
                )
            if not cs:
                cs = simpledialog.askstring(
                    'Spotify Client Secret', 
                    'Enter your Spotify Client Secret\n'
                    '(from developer.spotify.com/dashboard)\n\n'
                    'Copy and paste directly - do NOT type it manually:\n\n'
                    'Hint: It should be ~32 chars long'
                )

            if not cid or not cs:
                messagebox.showerror("Setup required", "Cannot proceed without Client ID and Secret.\n\nGet them from https://developer.spotify.com/dashboard")
                return

            # Persist client id/secret immediately so user is not re-prompted next launch
            try:
                save_cfg = {}
                if os.path.exists(cfg_path):
                    with open(cfg_path, 'r', encoding='utf-8') as f:
                        save_cfg = json.load(f)
                save_cfg["client_id"] = base64.b64encode(cid.encode()).decode()
                save_cfg["client_secret"] = base64.b64encode(cs.encode()).decode()
                os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
                with open(cfg_path, "w", encoding='utf-8') as f:
                    json.dump(save_cfg, f, indent=2)
            except Exception:
                pass

            # Show simple dialog
            dialog = tk.Toplevel(self)
            dialog.title('Sign in to Spotify')
            dialog.geometry('550x350')
            dialog.transient(self)
            
            instructions = (
                "One-time setup:\n\n"
                "1. Go to developer.spotify.com/dashboard\n"
                "2. Click on your app\n"
                "3. Click 'Edit Settings'\n"
                "4. Under 'Redirect URIs', add exactly this:\n"
                "   http://127.0.0.1:8888/callback\n"
                "   (Spotify allows localhost IPs for development)\n"
                "5. Click 'Save'\n\n"
                "Login flow note (Safari/Chrome):\n"
                "- After you sign in, Spotify redirects to http://127.0.0.1:8888/callback\n"
                "- There is no server running there, so seeing 'cannot connect to server' is normal\n"
                "- Keep that page open, copy the FULL address bar URL (it includes ?code=...), then paste it below."
            )
            
            ttk.Label(dialog, text=instructions, wraplength=500, justify='left', font=('Arial', 10)).pack(pady=15, padx=20)
            
            # Show what Client ID is being used
            client_id_display = f"Using Client ID: {cid[:30]}{'...' if len(cid) > 30 else ''}"
            ttk.Label(dialog, text=client_id_display, wraplength=500, justify='left', font=('Arial', 8), foreground='gray').pack(pady=5, padx=20)
            
            # Build auth URL - use 127.0.0.1 which Spotify accepts
            auth_params = {
                'client_id': cid,
                'response_type': 'code',
                'redirect_uri': 'http://127.0.0.1:8888/callback',
                'scope': 'user-read-private user-library-read'
            }
            
            from urllib.parse import urlencode
            auth_url = f"https://accounts.spotify.com/authorize?{urlencode(auth_params)}"
            
            # Validate URL looks reasonable
            if not cid or len(cid) < 10:
                messagebox.showerror("Invalid Client ID", f"Client ID appears invalid: '{cid}'")
                dialog.destroy()
                return

            # Quick helper to extract code from a pasted blob (URL or raw code)
            def _extract_code(text):
                if not text:
                    return None
                text = text.strip()
                # If user pasted only the code
                if len(text) > 0 and 'code=' not in text and 'http' not in text:
                    return text
                try:
                    from urllib.parse import urlparse, parse_qs
                    parsed = urlparse(text)
                    qs = parse_qs(parsed.query)
                    return qs.get('code', [None])[0]
                except Exception:
                    try:
                        return text.split('code=')[1].split('&')[0]
                    except Exception:
                        return None
            
            def open_browser():
                try:
                    print(f"DEBUG: Opening URL: {auth_url}")
                    import subprocess
                    import platform
                    
                    # On macOS, try using 'open' command first
                    if platform.system() == 'Darwin':
                        try:
                            subprocess.run(['open', auth_url], check=True, timeout=5)
                            messagebox.showinfo("Browser opened", "Check your browser for Spotify login page.")
                            return
                        except Exception as mac_err:
                            print(f"DEBUG: macOS 'open' command failed: {mac_err}")
                    
                    # Fallback to webbrowser module
                    result = webbrowser.open(auth_url)
                    print(f"DEBUG: webbrowser.open returned: {result}")
                    if result:
                        messagebox.showinfo("Browser opened", "Check your browser for Spotify login page.")
                    else:
                        messagebox.showwarning("Browser Issue", "Browser may not have opened.\n\nCopy the URL below and paste it manually into your browser.")
                except Exception as e:
                    print(f"DEBUG: Browser error: {e}")
                    import traceback
                    traceback.print_exc()
                    messagebox.showerror("Browser error", f"Could not open browser: {e}\n\nCopy the URL shown below and paste it into your browser manually.")
            
            ttk.Button(dialog, text='Open Spotify Login', command=open_browser, padding=10).pack(pady=10)
            
            ttk.Label(dialog, text='Or manually copy this URL:', wraplength=500).pack(pady=(15, 5))
            
            url_display = tk.Text(dialog, height=2, width=60, wrap='word')
            url_display.pack(pady=5, padx=10)
            url_display.insert('1.0', auth_url)
            url_display.config(state='disabled')
            
            copy_btn = ttk.Button(dialog, text='Copy URL to Clipboard', 
                                 command=lambda: (dialog.clipboard_clear(), dialog.clipboard_append(auth_url), messagebox.showinfo("Copied", "URL copied to clipboard")))
            copy_btn.pack(pady=5)
            
            # Also save URL to a file for easy access
            def save_url_to_file():
                url_file = os.path.expanduser("~/Desktop/spotify_login_url.txt")
                try:
                    with open(url_file, 'w') as f:
                        f.write(auth_url)
                    messagebox.showinfo("Saved", f"URL saved to: {url_file}")
                except Exception as e:
                    messagebox.showerror("Error", f"Could not save URL: {e}")
            
            ttk.Button(dialog, text='Save URL to Desktop', command=save_url_to_file).pack(pady=5)
            
            ttk.Label(dialog, text='After signing in, paste the URL from your browser:', wraplength=500).pack(pady=(15, 5))
            
            url_entry = tk.Text(dialog, height=2, width=60, wrap='word')
            url_entry.pack(pady=5, padx=10)

            # Helper to pull from clipboard automatically
            def paste_from_clipboard():
                try:
                    clip = dialog.clipboard_get()
                    url_entry.delete('1.0', 'end')
                    url_entry.insert('1.0', clip)
                except Exception:
                    messagebox.showwarning("Clipboard", "Could not read from clipboard; please paste manually")
            ttk.Button(dialog, text='Paste from Clipboard', command=paste_from_clipboard).pack(pady=4)
            
            result_container = {'token': None}
            
            def submit():
                resp = url_entry.get('1.0', 'end').strip()
                if not resp:
                    return

                code = _extract_code(resp)
                if not code:
                    messagebox.showerror("Error", "Could not find 'code' in what you pasted.\nPaste the full redirect URL or the code value itself.")
                    return

                # Show the extracted code for clarity and remind about single-use / expiration
                try:
                    messagebox.showinfo("Code detected", f"Using authorization code:\n{code}\n\nNote: Codes are single-use and expire quickly. If this fails, click 'Open Spotify Login' again and paste the new URL.")
                except Exception:
                    pass
                
                # Exchange code for token
                try:
                    token_data = {
                        'grant_type': 'authorization_code',
                        'code': code,
                        'redirect_uri': 'http://127.0.0.1:8888/callback',
                        'client_id': cid,
                        'client_secret': cs
                    }
                    
                    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                    resp = requests.post('https://accounts.spotify.com/api/token', data=token_data, headers=headers, timeout=10)
                    
                    # Log the response for debugging
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Token exchange response: {resp.status_code} - {resp.text}")
                    
                    resp.raise_for_status()
                    token_info = resp.json()
                    
                    # Add expires_at if not present
                    import time
                    if 'expires_at' not in token_info:
                        token_info['expires_at'] = int(time.time()) + token_info.get('expires_in', 3600)
                    
                    result_container['token'] = token_info.get('access_token')
                    result_container['token_info'] = token_info  # Store full token info with refresh_token
                    dialog.destroy()
                except requests.exceptions.HTTPError as e:
                    error_body = e.response.text if hasattr(e.response, 'text') else str(e)
                    messagebox.showerror("Token Exchange Failed", 
                        f"Spotify rejected the request:\n\n{error_body}\n\n"
                        f"Make sure:\n"
                        f"1. Client ID is correct\n"
                        f"2. Client Secret is correct\n"
                        f"3. Redirect URI 'http://127.0.0.1:8888/callback' is added to Spotify app settings")
                except Exception as e:
                    messagebox.showerror("Error", f"Login failed: {e}")
            
            ttk.Button(dialog, text='Submit', command=submit, padding=10).pack(pady=10)
            
            dialog.wait_window()
            
            access_token = result_container.get('token')
            token_info = result_container.get('token_info')
            if not access_token:
                return

            # Set global client
            sp = SpotifyClient(access_token=access_token)
            set_global_spotify(sp)
            
            # Save credentials (including refresh token and expiry)
            save_cfg = {}
            try:
                if os.path.exists(cfg_path):
                    with open(cfg_path, 'r', encoding='utf-8') as f:
                        save_cfg = json.load(f)
            except Exception:
                pass
            
            try:
                # Encode credentials
                cid_b64 = base64.b64encode(cid.encode()).decode()
                cs_b64 = base64.b64encode(cs.encode()).decode()
                access_token_b64 = base64.b64encode(access_token.encode()).decode()
                
                save_cfg["client_id"] = cid_b64
                save_cfg["client_secret"] = cs_b64
                save_cfg["access_token"] = access_token_b64
                
                # Store full token info for refresh capability (only JSON-serializable parts)
                if token_info:
                    token_info_to_save = {}
                    for key in ['access_token', 'refresh_token', 'expires_at', 'expires_in', 'token_type', 'scope']:
                        if key in token_info:
                            token_info_to_save[key] = token_info[key]
                    if token_info_to_save:
                        save_cfg["token_info"] = token_info_to_save
                
                os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
                with open(cfg_path, "w", encoding='utf-8') as f:
                    json.dump(save_cfg, f, indent=2)
            except Exception as e:
                messagebox.showerror("Save error", f"Could not save credentials: {e}")
                return

            try:
                self._auth_status.set('Signed in')
            except Exception:
                pass
            messagebox.showinfo("Success", "Successfully signed in to Spotify!")
            
        except Exception as exc:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Sign-in failed: {exc}")

    def _logout_spotify(self):
        try:
            from myspotipy.client import clear_global_spotify
            clear_global_spotify()
        except Exception:
            pass
        # remove saved access_token from config if present
        try:
            cfg_path = os.path.join(os.path.expanduser('~'), '.myspotipy', 'config.json')
            if os.path.exists(cfg_path):
                try:
                    with open(cfg_path, 'r', encoding='utf-8') as f:
                        cfg = json.load(f)
                except Exception:
                    cfg = {}
                if cfg.get('access_token'):
                    cfg.pop('access_token', None)
                    try:
                        with open(cfg_path, 'w', encoding='utf-8') as f:
                            json.dump(cfg, f)
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            self._auth_status.set('Not signed in')
        except Exception:
            pass
        messagebox.showinfo('Signed out', 'Signed out of Spotify')

    def _hide_search_panel(self):
        try:
            if getattr(self, '_search_visible', False):
                self._add_selected_btn.pack_forget()
                self.search_frame.pack_forget()
                self.right_frame.pack_forget()
                self._search_visible = False
                # restore geometry if we saved it
                try:
                    if getattr(self, '_saved_geometry', None):
                        # attempt to parse and restore original geometry
                        try:
                            self.geometry(self._saved_geometry)
                        except Exception:
                            pass
                        self._saved_geometry = None
                except Exception:
                    pass
                try:
                    self._close_search_btn.pack_forget()
                except Exception:
                    pass
        except Exception:
            pass

    def _save_dance_row(self, idx, row):
        # update in memory and write entire CSV
        data = self.db._read_all_rows()
        data[idx] = row
        self.db._write_all_rows(data)
        self._load_dances()

    def _on_dance_select(self):
        sel = self.dance_list.curselection()
        if not sel:
            return
        idx = sel[0]
        row = self.db._read_all_rows()[idx]
        songs_json = row.get('songs') or '[]'
        try:
            songs = json.loads(songs_json)
        except Exception:
            songs = []
        self.songs_list.delete(0, tk.END)
        for s in songs:
            # s may be dict or string
            if isinstance(s, dict):
                title = s.get('name') or s.get('title') or ''
                artist = s.get('artist') or s.get('artist_name') or ''
                self.songs_list.insert(tk.END, f"{title} — {artist}")
            else:
                self.songs_list.insert(tk.END, str(s))
        # migrate: remove legacy keys (genre, album_url) from stored songs but KEEP track_id for BPM fetches
        mutated = False
        for i, s in enumerate(songs):
            if isinstance(s, dict):
                removed = False
                for k in ('genre', 'album_url'):
                    if k in s:
                        s.pop(k, None)
                        removed = True
                if removed:
                    mutated = True
        if mutated:
            # persist cleaned songs
            row['songs'] = json.dumps(songs)
            data = self.db._read_all_rows()
            data[idx] = row
            self.db._write_all_rows(data)
            # and reload to reflect any storage normalization
            self._load_dances()
            return
        
        # Update dance info display
        self._update_dance_info_display(row)

    def _update_dance_info_display(self, row):
        """Update the dance info text widget with level and notes."""
        try:
            self._dance_info_text.config(state='normal')
            self._dance_info_text.delete('1.0', tk.END)
            
            level = row.get('level', '')
            notes = row.get('notes', '')
            
            info_lines = []
            if level:
                info_lines.append(f"Level: {level}")
            if notes:
                info_lines.append(f"\nNotes:\n{notes}")
            
            if info_lines:
                self._dance_info_text.insert('1.0', '\n'.join(info_lines))
            else:
                self._dance_info_text.insert('1.0', 'No info yet. Click Edit to add.')
            
            self._dance_info_text.config(state='disabled')
        except Exception:
            pass

    def _new_dance(self):
        name = simpledialog.askstring("New Dance", "Dance name:")
        if not name:
            return
        row = {"name": name, "level": "", "songs": json.dumps([]), "notes": ""}
        self.db.add_record(row)
        self._load_dances()

    def _edit_dance(self):
        """Edit dance information (name, level, choreographers, release_date, notes)."""
        sel = self.dance_list.curselection()
        if not sel:
            messagebox.showwarning("No selection", "Select a dance to edit.")
            return
        idx = sel[0]
        rows = self.db._read_all_rows()
        if idx < 0 or idx >= len(rows):
            return
        row = rows[idx]
        
        # Create edit dialog
        dialog = tk.Toplevel(self)
        dialog.title("Edit Dance")
        dialog.geometry("550x500")
        dialog.transient(self)
        
        # Name field
        ttk.Label(dialog, text="Dance Name:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        name_var = tk.StringVar(value=row.get('name', ''))
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=40)
        name_entry.grid(row=0, column=1, sticky=tk.W, padx=10, pady=5)
        
        # Choreographers field
        ttk.Label(dialog, text="Choreographer(s):").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        # Parse existing choreographers from JSON
        choreo_str = ''
        try:
            choreo_list = json.loads(row.get('choreographers', '[]'))
            if choreo_list:
                choreo_str = ' & '.join([
                    f"{c['name']} ({c['location']})" if c.get('location') else c['name']
                    for c in choreo_list
                ])
        except:
            pass
        choreo_var = tk.StringVar(value=choreo_str)
        choreo_entry = ttk.Entry(dialog, textvariable=choreo_var, width=40)
        choreo_entry.grid(row=1, column=1, sticky=tk.W, padx=10, pady=5)
        
        # Release Date field
        ttk.Label(dialog, text="Release Date:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        release_date_var = tk.StringVar(value=row.get('release_date', ''))
        release_date_entry = ttk.Entry(dialog, textvariable=release_date_var, width=40)
        release_date_entry.grid(row=2, column=1, sticky=tk.W, padx=10, pady=5)
        
        # Level field
        ttk.Label(dialog, text="Level:").grid(row=3, column=0, sticky=tk.W, padx=10, pady=5)
        level_var = tk.StringVar(value=row.get('level', ''))
        level_entry = ttk.Combobox(dialog, textvariable=level_var, width=37, values=[
            "Absolute Beginner",
            "Beginner",
            "Improver",
            "Intermediate",
            "Advanced"
        ])
        level_entry.grid(row=3, column=1, sticky=tk.W, padx=10, pady=5)
        
        # Notes field
        ttk.Label(dialog, text="Notes:").grid(row=4, column=0, sticky=tk.NW, padx=10, pady=5)
        notes_text = tk.Text(dialog, width=40, height=10, wrap='word')
        notes_text.grid(row=4, column=1, sticky=tk.W, padx=10, pady=5)
        notes_text.insert('1.0', row.get('notes', ''))
        
        def save():
            new_name = name_var.get().strip()
            if not new_name:
                messagebox.showerror("Invalid name", "Dance name cannot be empty.")
                return
            
            # Parse choreographers from text field
            choreo_text = choreo_var.get().strip()
            choreographers = []
            if choreo_text:
                import re
                choreo_parts = re.split(r'\s+(?:&|and)\s+', choreo_text)
                for part in choreo_parts:
                    match = re.match(r'([^(]+)(?:\(([^)]+)\))?', part.strip())
                    if match:
                        name = match.group(1).strip()
                        location = match.group(2).strip() if match.group(2) else ''
                        choreographers.append({
                            'name': name,
                            'location': location
                        })
            
            row['name'] = new_name
            row['choreographers'] = json.dumps(choreographers)
            row['release_date'] = release_date_var.get().strip()
            row['level'] = level_var.get().strip()
            row['notes'] = notes_text.get('1.0', 'end-1c')
            
            rows[idx] = row
            self.db._write_all_rows(rows)
            self._reload_and_restore_dance(idx)
            dialog.destroy()
        
        def cancel():
            dialog.destroy()
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Save", command=save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=cancel).pack(side=tk.LEFT, padx=5)
        
        dialog.grab_set()

    def _delete_dance(self):
        sel = self.dance_list.curselection()
        if not sel:
            return
        idx = sel[0]
        row = self.db._read_all_rows()[idx]
        name = row.get('name')
        self.db.delete_record('name', name)
        self._load_dances()

    def _remove_song(self):
        dsel = self.dance_list.curselection()
        ssel = self.songs_list.curselection()
        if not dsel or not ssel:
            return
        didx = dsel[0]
        sidx = ssel[0]
        rows = self.db._read_all_rows()
        row = rows[didx]
        try:
            songs = json.loads(row.get('songs') or '[]')
        except Exception:
            songs = []
        if 0 <= sidx < len(songs):
            songs.pop(sidx)
        row['songs'] = json.dumps(songs)
        self.db._write_all_rows(rows)
        # refresh and keep dance selected
        self._reload_and_restore_dance(didx)
        # clear details after removal
        self._set_song_details('')

    def _background_fetch_bpm_worker(self, track_id: Optional[str], name: Optional[str], artist: Optional[str], dance_idx: int, song_idx: int):
        # Background worker: try to obtain BPM for a song from Copperknob and persist it into the CSV
        bpm = None
        err_info = None

        # Try to fetch BPM from Copperknob (line dance database)
        if name:
            try:
                from copperknob_scraper import get_bpm_from_copperknob
                bpm = get_bpm_from_copperknob(name, artist)
            except Exception as e:
                err_info = str(e)
                bpm = None

        # If bpm found, persist it into CSV
        if bpm is not None:
            try:
                rows = self.db._read_all_rows()
                if 0 <= dance_idx < len(rows):
                    row = rows[dance_idx]
                    try:
                        songs = json.loads(row.get('songs') or '[]')
                    except Exception:
                        songs = []
                    if 0 <= song_idx < len(songs) and isinstance(songs[song_idx], dict):
                        songs[song_idx]['bpm'] = bpm
                        row['songs'] = json.dumps(songs)
                        rows[dance_idx] = row
                        self.db._write_all_rows(rows)
                        # refresh UI
                        try:
                            self._load_dances()
                        except Exception:
                            pass
            except Exception:
                pass
        else:
            # log failure
            try:
                logp = os.path.join(os.path.expanduser('~'), '.myspotipy', 'dance_gui_error.log')
                os.makedirs(os.path.dirname(logp), exist_ok=True)
                with open(logp, 'a', encoding='utf-8') as f:
                    f.write(f"Background BPM fetch failed for {name or track_id}: {err_info}\n")
            except Exception:
                pass

    def _set_song_details(self, text: str, album_url: str = None):
        try:
            # handle album art
            if album_url and Image and ImageTk:
                try:
                    import requests

                    resp = requests.get(album_url, timeout=8)
                    if resp.ok:
                        img = Image.open(io.BytesIO(resp.content))
                        img.thumbnail((160, 160))
                        self._album_photo = ImageTk.PhotoImage(img)
                        self._album_art_label.config(image=self._album_photo)
                    else:
                        self._album_art_label.config(image='')
                except Exception:
                    self._album_art_label.config(image='')
            else:
                # clear image
                try:
                    self._album_art_label.config(image='')
                except Exception:
                    pass

            self._song_details.config(state='normal')
            self._song_details.delete('1.0', tk.END)
            if text:
                self._song_details.insert(tk.END, text)
            self._song_details.config(state='disabled')
        except Exception:
            pass

    def _open_in_spotify(self):
        """Open the currently selected song in the Spotify app."""
        dsel = self.dance_list.curselection()
        ssel = self.songs_list.curselection()
        if not dsel or not ssel:
            messagebox.showinfo("No Selection", "Please select a song first.")
            return
        didx = dsel[0]
        sidx = ssel[0]
        rows = self.db._read_all_rows()
        if didx < 0 or didx >= len(rows):
            return
        row = rows[didx]
        try:
            songs = json.loads(row.get('songs') or '[]')
        except Exception:
            songs = []
        if sidx < 0 or sidx >= len(songs):
            return
        s = songs[sidx]
        
        # Try to get track_id from the song data
        track_id = None
        if isinstance(s, dict):
            track_id = s.get('track_id')
        
        if track_id:
            # Use spotify: URI to open in the app
            import subprocess
            spotify_uri = f"spotify:track:{track_id}"
            try:
                subprocess.run(['open', spotify_uri], check=True)
                return
            except Exception as e:
                print(f"Failed to open Spotify URI: {e}")
        
        # Fallback: search for the song
        if isinstance(s, dict):
            name = s.get('name', '')
            artist = s.get('artist', '')
            if name and artist:
                try:
                    sp = get_global_spotify(create_if_missing=True)
                    if sp:
                        results = sp.search_tracks(name, artist=artist, k=1)
                        if results:
                            track_id = results[0].get('raw', {}).get('id')
                            if track_id:
                                import subprocess
                                spotify_uri = f"spotify:track:{track_id}"
                                subprocess.run(['open', spotify_uri], check=True)
                                return
                except Exception as e:
                    print(f"Failed to search and open: {e}")
        
        messagebox.showinfo("Cannot Open", "Could not find this song on Spotify.")
    
    def _on_song_select(self):
        # Show full info for the selected song in the Songs list
        dsel = self.dance_list.curselection()
        ssel = self.songs_list.curselection()
        if not dsel or not ssel:
            self._set_song_details('')
            return
        didx = dsel[0]
        sidx = ssel[0]
        rows = self.db._read_all_rows()
        if didx < 0 or didx >= len(rows):
            self._set_song_details('')
            return
        row = rows[didx]
        try:
            songs = json.loads(row.get('songs') or '[]')
        except Exception:
            songs = []
        if sidx < 0 or sidx >= len(songs):
            self._set_song_details('')
            return
        s = songs[sidx]
        if isinstance(s, dict):
            parts = [f"Name: {s.get('name','')}", f"Artist: {s.get('artist','')}", f"BPM: {s.get('bpm', '')}"]
            # include any other keys except hidden extras like album_url or track_id
            extra = {k: v for k, v in s.items() if k not in ('name', 'artist', 'bpm', 'album_url', 'track_id')}
            if extra:
                parts.append('Extras:')
                for k, v in extra.items():
                    parts.append(f"  {k}: {v}")
            text = '\n'.join(parts)
        else:
            text = str(s)
        # attempt to fetch album art on-the-fly (do not persist url/id)
        album_url = None
        if isinstance(s, dict):
            try:
                # try to use an available Spotify client to find the track and album art
                try:
                    sp = get_global_spotify(create_if_missing=False)
                except Exception:
                    sp = None
                if sp is None:
                    try:
                        sp = get_global_spotify(create_if_missing=True)
                    except Exception:
                        sp = None
                if sp is not None:
                    name = s.get('name') or ''
                    artist = s.get('artist') or None
                    if name:
                        try:
                            results = sp.search_tracks(name, artist=artist, k=1)
                            if results:
                                raw = results[0].get('raw') or {}
                                album = raw.get('album', {})
                                images = album.get('images', [])
                                if images:
                                    album_url = images[0].get('url')
                        except Exception:
                            album_url = None
            except Exception:
                album_url = None
        self._set_song_details(text, album_url=album_url)

    def _add_selected_song_to_dance(self):
        try:
            sel = self.dance_list.curselection()
            if not sel:
                messagebox.showwarning("No dance selected", "Select a dance to add the song to.")
                return
            idx = sel[0]
            dance_rows = self.db._read_all_rows()
            # guard against index errors
            if idx < 0 or idx >= len(dance_rows):
                messagebox.showerror("Selection error", "Selected dance index is out of range.")
                return
            row = dance_rows[idx]
            track = self.search_frame.get_selected_track()
            if not track:
                messagebox.showwarning("No track selected", "Select a track in the search results first.")
                return

            # create Song instance using create_from_spotify (may fetch BPM)
            try:
                sp = get_global_spotify(create_if_missing=True)
            except Exception:
                sp = None
            song = create_from_spotify(track, sp=sp)

            # serialize song to simple dict (no genre); include album art URL when available
            album_url = None
            try:
                raw = track.get('raw') or {}
                album = raw.get('album', {})
                images = album.get('images', [])
                if images:
                    # prefer the first (largest) image
                    album_url = images[0].get('url')
            except Exception:
                album_url = None

            # Persist track_id so later BPM fetches can reliably call audio_features
            song_dict = {"name": song.name, "artist": song.artist, "bpm": song.bpm}
            try:
                tid = track.get('id')
                if tid:
                    song_dict['track_id'] = tid
            except Exception:
                tid = None

            # Try to fetch BPM immediately from Copperknob (line dance database)
            if song_dict.get('bpm') is None:
                try:
                    from copperknob_scraper import get_bpm_from_copperknob
                    bpm = get_bpm_from_copperknob(song_dict.get('name'), song_dict.get('artist'))
                    if bpm:
                        song_dict['bpm'] = bpm
                except Exception:
                    pass
            try:
                songs = json.loads(row.get('songs') or '[]')
            except Exception:
                songs = []
            songs.append(song_dict)
            row['songs'] = json.dumps(songs)
            dance_rows[idx] = row
            # persist and reload
            self.db._write_all_rows(dance_rows)
            self._load_dances()
            # schedule background BPM fetch if we have a track id and bpm is missing
            if song_dict.get('bpm') is None:
                threading.Thread(
                    target=self._background_fetch_bpm_worker,
                    args=(tid, song_dict.get('name'), song_dict.get('artist'), idx, len(songs)-1),
                    daemon=True,
                ).start()
            # refresh songs view and keep dance selected
            self._reload_and_restore_dance(idx)
            # hide search panel after add
            self._hide_search_panel()
            messagebox.showinfo("Added", f"Added '{song.name}' to dance '{row.get('name')}'.")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            # write a small local log so user can inspect
            try:
                logp = os.path.join(os.path.expanduser('~'), '.myspotipy', 'dance_gui_error.log')
                os.makedirs(os.path.dirname(logp), exist_ok=True)
                with open(logp, 'a', encoding='utf-8') as f:
                    f.write(tb + '\n')
            except Exception:
                pass
            messagebox.showerror('Add failed', f'Failed to add song to dance: {e}\nSee {logp} for details.')

    def _fetch_bpm_for_selected_song(self):
        """Attempt to fetch BPM for the currently selected song (uses stored track_id)."""
        dsel = self.dance_list.curselection()
        ssel = self.songs_list.curselection()
        if not dsel or not ssel:
            messagebox.showwarning("No selection", "Select a dance and a song first.")
            return
        didx = dsel[0]
        sidx = ssel[0]
        rows = self.db._read_all_rows()
        if didx < 0 or didx >= len(rows):
            messagebox.showerror("Selection error", "Selected dance index is out of range.")
            return
        row = rows[didx]
        try:
            songs = json.loads(row.get('songs') or '[]')
        except Exception:
            songs = []
        if sidx < 0 or sidx >= len(songs):
            messagebox.showwarning("No song", "Selected song index out of range.")
            return
        s = songs[sidx]
        if not isinstance(s, dict):
            messagebox.showinfo("No metadata", "Selected item has no metadata to fetch BPM.")
            return
        
        name = s.get('name') or ''
        artist = s.get('artist') or None
        
        if not name:
            messagebox.showinfo("No song name", "Selected song has no name; cannot fetch BPM.")
            return
        
        # Try to fetch BPM from Copperknob (line dance database)
        try:
            from copperknob_scraper import get_bpm_from_copperknob
            bpm = get_bpm_from_copperknob(name, artist)
            
            if bpm:
                s['bpm'] = bpm
                # persist
                row['songs'] = json.dumps(songs)
                rows[didx] = row
                self.db._write_all_rows(rows)
                self._load_dances()
                messagebox.showinfo("BPM fetched", f"Fetched BPM from Copperknob: {bpm}")
                return
            else:
                messagebox.showwarning("Not found", "BPM not found on Copperknob for this song. You can use the 'Edit BPM' button to enter it manually.")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            try:
                logp = os.path.join(os.path.expanduser('~'), '.myspotipy', 'dance_gui_error.log')
                os.makedirs(os.path.dirname(logp), exist_ok=True)
                with open(logp, 'a', encoding='utf-8') as f:
                    f.write(tb + '\n')
            except Exception:
                pass
            messagebox.showerror("Fetch failed", f"Failed to fetch BPM from Copperknob: {e}")

    def _edit_bpm_for_selected_song(self):
        # allow user to enter BPM manually and persist it
        dsel = self.dance_list.curselection()
        ssel = self.songs_list.curselection()
        if not dsel or not ssel:
            messagebox.showwarning("No selection", "Select a dance and a song first.")
            return
        didx = dsel[0]
        sidx = ssel[0]
        rows = self.db._read_all_rows()
        if didx < 0 or didx >= len(rows):
            messagebox.showerror("Selection error", "Selected dance index is out of range.")
            return
        row = rows[didx]
        try:
            songs = json.loads(row.get('songs') or '[]')
        except Exception:
            songs = []
        if sidx < 0 or sidx >= len(songs):
            messagebox.showwarning("No song", "Selected song index out of range.")
            return
        s = songs[sidx]
        if not isinstance(s, dict):
            messagebox.showinfo("No metadata", "Selected item has no metadata to edit.")
            return
        # prompt for BPM
        try:
            cur = s.get('bpm')
            from tkinter import simpledialog

            val = simpledialog.askfloat("Edit BPM", "Enter BPM (positive number):", initialvalue=cur)
            if val is None:
                return
            if val <= 0:
                messagebox.showerror("Invalid BPM", "BPM must be a positive number.")
                return
            s['bpm'] = float(val)
            row['songs'] = json.dumps(songs)
            rows[didx] = row
            self.db._write_all_rows(rows)
            self._load_dances()
            messagebox.showinfo("Saved", f"Saved BPM: {val}")
        except Exception as e:
            messagebox.showerror("Save failed", f"Failed to save BPM: {e}")

    def _remove_selected_song_from_dance(self):
        # convenience wrapper to remove the currently selected song (from details)
        dsel = self.dance_list.curselection()
        ssel = self.songs_list.curselection()
        if not dsel or not ssel:
            messagebox.showwarning("No selection", "Select a dance and a song first.")
            return
        didx = dsel[0]
        sidx = ssel[0]
        rows = self.db._read_all_rows()
        if didx < 0 or didx >= len(rows):
            messagebox.showerror("Selection error", "Selected dance index is out of range.")
            return
        row = rows[didx]
        try:
            songs = json.loads(row.get('songs') or '[]')
        except Exception:
            songs = []
        if sidx < 0 or sidx >= len(songs):
            messagebox.showwarning("No song", "Selected song index out of range.")
            return
        songs.pop(sidx)
        row['songs'] = json.dumps(songs)
        rows[didx] = row
        self.db._write_all_rows(rows)
        # refresh and restore selection
        self._reload_and_restore_dance(didx)
        self._set_song_details('')


def main():
    app = DanceManagerApp()
    app.mainloop()

if __name__ == '__main__':
    main()

