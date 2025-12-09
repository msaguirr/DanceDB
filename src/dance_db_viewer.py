import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import os

DB_PATH = os.path.join(os.path.expanduser("~"), "dances.db")

class DanceDBViewer(tk.Tk):
    def _on_row_click(self, event):
        # Ensure details panel updates on any row click
        self._on_row_select(event)
    DANCE_LEVEL_ORDER = [
        "Absolute Beginner", "Beginner", "Improver", "Intermediate", "Advanced"
    ]
    LEVEL_ORDER = {level: i for i, level in enumerate(DANCE_LEVEL_ORDER)}
    KEYWORD_MODIFIERS = {
        "easy": -0.1,
        "low": -0.1,
        "high": 0.2,
        "phrased": 0.3,
    }

    def _level_sort_key(self, value):
        import re
        # Find main level
        main_level = next((lvl for lvl in self.DANCE_LEVEL_ORDER if lvl.lower() in value.lower()), None)
        base = self.LEVEL_ORDER.get(main_level, len(self.DANCE_LEVEL_ORDER))
        # Modifiers
        modifier = 0
        easy_low_found = False
        for word, val in self.KEYWORD_MODIFIERS.items():
            if word in ("easy", "low"):
                if re.search(rf"\\b{word}\\b", value, re.IGNORECASE):
                    easy_low_found = True
            else:
                if re.search(rf"\\b{word}\\b", value, re.IGNORECASE):
                    modifier += val
        if easy_low_found:
            modifier += self.KEYWORD_MODIFIERS["easy"]  # -0.1
        # Always use (base, modifier, value.lower()) for stable sort
        return (base, modifier, value.lower())
    def __init__(self):
        super().__init__()
        self.title("DanceDB Viewer")
        self.geometry("900x550")
        self.search_var = tk.StringVar()
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.Frame(main_frame, width=880)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        left_frame.pack_propagate(False)

        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        search_entry.pack(side=tk.LEFT, padx=4)
        ttk.Button(search_frame, text="Search", command=self._load_data).pack(side=tk.LEFT, padx=8)
        search_entry.bind('<Return>', lambda e: self._load_data())

        self.tree = ttk.Treeview(left_frame, columns=("name", "level", "priority", "category", "songs"), show="headings")
        import tkinter.font as tkfont
        # Use TkDefaultFont for measurement (ttk.Treeview does not support -font option)
        tree_font = tkfont.nametofont("TkDefaultFont")
        # Use the actual dropdown lists from the main dance information comboboxes
        priority_options = ["", "Highest", "High", "Medium", "Low", "Lowest", "Never"]
        category_options = ["", "Learn next", "Learn soon", "Learn later"]
        # Level options from the main combobox (match actual dropdown values exactly)
        level_options = ["", "Absolute Beginner", "Beginner", "Improver", "Intermediate", "Advanced"]
        padding = 24
        extra_level_padding = 40  # Make level column wider than others
        priority_width = max(max(tree_font.measure(v) for v in priority_options), tree_font.measure("Priority")) + padding
        category_width = max(max(tree_font.measure(v) for v in category_options), tree_font.measure("Category")) + padding
        level_width = max(max(tree_font.measure(v) for v in level_options), tree_font.measure("Level")) + padding + extra_level_padding
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col.title(), command=lambda c=col: self._sort_by_column(c, False))
            if col == "priority":
                self.tree.column(col, width=priority_width, anchor=tk.W, minwidth=priority_width, stretch=False)
            elif col == "category":
                self.tree.column(col, width=category_width, anchor=tk.W, minwidth=category_width, stretch=False)
            elif col == "level":
                self.tree.column(col, width=level_width, anchor=tk.W, minwidth=level_width, stretch=False)
            elif col == "songs":
                self.tree.column(col, width=120, anchor=tk.W, stretch=True)
            else:
                self.tree.column(col, width=120, anchor=tk.W, stretch=False)

        # Save widths for later enforcement
        self._priority_width = priority_width
        self._category_width = category_width
        self._level_width = level_width
        self.tree.pack(fill=tk.BOTH, expand=True)
        # Details panel (right side)
        # Schedule column width enforcement after window is rendered
        self.after_idle(self._enforce_column_widths)

    def _enforce_column_widths(self):
        self.tree.column("priority", width=self._priority_width, minwidth=self._priority_width, stretch=False)
        self.tree.column("category", width=self._category_width, minwidth=self._category_width, stretch=False)
        self.tree.column("level", width=self._level_width, minwidth=self._level_width, stretch=False)
        self.tree.column("songs", width=120, stretch=True)
        # Bind events after packing
        self.tree.bind("<<TreeviewSelect>>", self._on_row_select)
        self.tree.bind("<Double-1>", self._on_row_double_click)
        self.tree.bind("<ButtonRelease-1>", self._on_row_click)


    def _load_data(self):
        self.tree.delete(*self.tree.get_children())
        search_filter = self.search_var.get().strip().lower()
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            query = "SELECT id, name, level, choreographers, release_date, priority, category, frequency, aka, notes, copperknob_id, songs FROM dances ORDER BY name"
            for row in c.execute(query):
                (db_id, name, level, choreographers, release_date, priority, category, frequency, aka, notes, copperknob_id, songs_json) = row
                match = True
                if search_filter:
                    # Match against dance name, song name, or song artist
                    if search_filter not in name.lower():
                        found = False
                        try:
                            import json
                            songs = json.loads(songs_json)
                            for song in songs:
                                if search_filter in str(song.get('song_name', '')).lower() or search_filter in str(song.get('artist', '')).lower():
                                    found = True
                                    break
                        except Exception:
                            found = False
                        if not found:
                            match = False
                if match:
                    # Parse songs for display
                    song_display = ""
                    try:
                        import json
                        songs = json.loads(songs_json)
                        song_display = ", ".join([f"{s.get('song_name','')} by {s.get('artist','')}" for s in songs if s.get('song_name') or s.get('artist')])
                    except Exception:
                        song_display = ""
                    self.tree.insert("", tk.END, values=(name, level, priority, category, song_display), iid=str(db_id))
            conn.close()
            # Enforce column widths after data is loaded
            self.tree.column("priority", width=self._priority_width, minwidth=self._priority_width, stretch=False)
            self.tree.column("category", width=self._category_width, minwidth=self._category_width, stretch=False)
            self.tree.column("level", width=self._level_width, minwidth=self._level_width, stretch=False)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data: {e}")

    def _on_row_select(self, event):
        # Resize window to show details panel
        print("_on_row_select called")
        print(f"event: {event}")
        self.geometry("1200x550")
        item = self.tree.selection()
        print(f"item selection: {item}")
        if not item:
            print("No item selected")
            return
        db_id = item[0]
        print(f"db_id to use: {db_id}")
        try:
            print(f"Selected db_id: {db_id}")
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT name, level, choreographers, release_date, priority, category, frequency, aka, notes, copperknob_id, songs FROM dances WHERE id=?", (db_id,))
            row = c.fetchone()
            print(f"Fetched row: {row}")
            conn.close()
            if not row:
                debug_msg = f"No row found for id={db_id}.\nCheck if the database and ids are correct."
                if hasattr(self, 'details_label'):
                    self.details_label.config(state='normal')
                    self.details_label.delete('1.0', tk.END)
                    self.details_label.insert(tk.END, debug_msg)
                    self.details_label.config(state='disabled')
                return
            (name, level, choreographers, release_date, priority, category, frequency, aka, notes, copperknob_id, songs_json) = row
            details = f"Name: {name}\nLevel: {level}\nChoreographers: {choreographers}\nRelease Date: {release_date}\nPriority: {priority}\nCategory: {category}\nFrequency: {frequency}\nAKA: {aka}\nNotes: {notes}\nCopperknob ID: {copperknob_id}\n"
            # Add songs
            try:
                import json
                songs = json.loads(songs_json)
                if songs:
                    details += "\nSongs:\n"
                    for i, song in enumerate(songs, 1):
                        details += f"  {i}. {song.get('song_name', '')} by {song.get('artist', '')}"
                        if song.get('genre'):
                            details += f" | Genre: {song.get('genre')}"
                        if song.get('bpm'):
                            details += f" | BPM: {song.get('bpm')}"
                        if song.get('spotify_url'):
                            details += f" | Spotify: {song.get('spotify_url')}"
                        details += "\n"
            except Exception:
                pass
            if hasattr(self, 'details_label'):
                self.details_label.config(state='normal')
                self.details_label.delete('1.0', tk.END)
                self.details_label.insert(tk.END, details)
                self.details_label.config(state='disabled')
        except Exception as e:
            debug_msg = f"Error loading details for id={db_id}: {e}"
            if hasattr(self, 'details_label'):
                self.details_label.config(state='normal')
                self.details_label.delete('1.0', tk.END)
                self.details_label.insert(tk.END, debug_msg)
                self.details_label.config(state='disabled')

    def _on_row_double_click(self, event):
        item = self.tree.selection()
        if not item:
            return
        values = self.tree.item(item[0], "values")
        details = "\n".join(f"{col.title()}: {val}" for col, val in zip(self.tree["columns"], values))
        messagebox.showinfo("Dance Details", details)

if __name__ == "__main__":
    app = DanceDBViewer()
    app.mainloop()
