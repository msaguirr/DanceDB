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

        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=0)  # search bar row
        main_frame.rowconfigure(1, weight=1)  # main content row


        # Search bar now above both frames
        search_frame = ttk.Frame(main_frame)
        search_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=6)
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        search_entry.pack(side=tk.LEFT, padx=4)
        ttk.Button(search_frame, text="Search", command=self._load_data).pack(side=tk.LEFT, padx=8)
        search_entry.bind('<Return>', lambda e: self._load_data())
        ttk.Button(search_frame, text="Delete Selected", command=self._delete_selected_row).pack(side=tk.LEFT, padx=8)

        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(0,8), pady=0)

        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=1, column=1, sticky="nsew", padx=0, pady=0)
        right_frame.grid(row=1, column=1, sticky="nsew", padx=(0,0), pady=0)

        self.tree = ttk.Treeview(left_frame, columns=("name", "level", "priority", "category", "songs"), show="headings")
        import tkinter.font as tkfont
        tree_font = tkfont.nametofont("TkDefaultFont")
        priority_options = ["", "Highest", "High", "Medium", "Low", "Lowest", "Never"]
        category_options = ["", "Learn next", "Learn soon", "Learn later"]
        level_options = ["", "Absolute Beginner", "Beginner", "Improver", "Intermediate", "Advanced"]
        padding = 24
        extra_level_padding = 40
        priority_width = max(max(tree_font.measure(v) for v in priority_options), tree_font.measure("Priority")) + padding
        category_width = max(max(tree_font.measure(v) for v in category_options), tree_font.measure("Category")) + padding
        level_width = max(max(tree_font.measure(v) for v in level_options), tree_font.measure("Level")) + padding + extra_level_padding
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col.title())
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
        self._priority_width = priority_width
        self._category_width = category_width
        self._level_width = level_width
        left_frame.rowconfigure(0, weight=1)
        left_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)
        right_frame.columnconfigure(0, weight=1)

        self.tree.grid(row=0, column=0, sticky="nsew")

        # Bind selection events after Treeview is placed
        self.tree.bind("<<TreeviewSelect>>", self._on_row_select)
        self.tree.bind("<Double-1>", self._on_row_double_click)
        self.tree.bind("<ButtonRelease-1>", self._on_row_click)

        # Details label (Text widget for multi-line info)
        self.details_label = tk.Text(
            right_frame,
            wrap=tk.WORD,
            state='disabled',
            font=tree_font,
            width=40,
            padx=0,
            pady=0,
            borderwidth=0,
            highlightthickness=0
        )
        self.details_label.grid(row=0, column=0, sticky="nsew", pady=(2,0))
        self.details_label.config(state='normal')
        self.details_label.delete('1.0', tk.END)
        self.details_label.config(state='disabled')

        # Notification label (non-blocking)
        self.notification_label = ttk.Label(self, text="", foreground="green", font=tree_font)
        self.notification_label.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=4)
        
    def _delete_selected_row(self):
        item = self.tree.selection()
        if not item:
            messagebox.showwarning("Delete", "No row selected.")
            return
        db_id = item[0]
        # Get dance name for confirmation
        dance_name = self.tree.item(db_id, "values")[0] if self.tree.item(db_id, "values") else "this dance"
        confirm_text = f"Delete '{dance_name}'?"
        # Custom dialog with switched buttons
        confirm_win = tk.Toplevel(self)
        confirm_win.title("Confirm Delete")
        confirm_win.transient(self)
        confirm_win.grab_set()
        ttk.Label(confirm_win, text=confirm_text, padding=16).pack(padx=16, pady=(16,8))
        btn_frame = ttk.Frame(confirm_win)
        btn_frame.pack(pady=(0,16))
        def do_delete():
            confirm_win.destroy()
            self._actually_delete_row(db_id)
        def do_cancel():
            confirm_win.destroy()
        ttk.Button(btn_frame, text="Delete", command=do_delete).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text="Cancel", command=do_cancel).pack(side=tk.LEFT, padx=8)
        confirm_win.update_idletasks()
        # Center the popup over the main window
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (confirm_win.winfo_width() // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (confirm_win.winfo_height() // 2)
        confirm_win.geometry(f"+{x}+{y}")
        confirm_win.wait_window()
        return
    def _actually_delete_row(self, db_id):
        try:
            conn = sqlite3.connect(DB_PATH)
            c.execute("DELETE FROM dances WHERE id=?", (db_id,))
            conn.commit()
            conn.close()
            # Only delete from Treeview if item exists
            if db_id in self.tree.get_children():
                self.tree.delete(db_id)
            # Show non-blocking notification
            self.notification_label.config(text="Row deleted successfully.")
            self.after(2500, lambda: self.notification_label.config(text=""))
        except Exception as e:
            messagebox.showerror("Delete Error", f"Failed to delete row: {e}")

        # Removed duplicate Treeview creation and column setup; Treeview is created in _build_ui
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
        # Always show details panel, just clear/disable if nothing selected
        item = self.tree.selection()
        if not item:
            self.details_label.config(state='normal')
            self.details_label.delete('1.0', tk.END)
            self.details_label.config(state='disabled')
            self.geometry("900x550")
            return
        db_id = item[0]
        self.details_label.config(state='normal')
        self.details_label.delete('1.0', tk.END)
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT name, level, choreographers, release_date, priority, category, frequency, aka, notes, copperknob_id, songs FROM dances WHERE id=?", (db_id,))
            row = c.fetchone()
            conn.close()
            if not row:
                debug_msg = f"No row found for id={db_id}.\nCheck if the database and ids are correct."
                self.details_label.insert(tk.END, debug_msg)
                self.details_label.config(state='disabled')
                return
            (name, level, choreographers, release_date, priority, category, frequency, aka, notes, copperknob_id, songs_json) = row
            details = f"Name: {name}\nLevel: {level}\nChoreographers: {choreographers}\nRelease Date: {release_date}\nPriority: {priority}\nCategory: {category}\nFrequency: {frequency}\n"
            if aka and aka.strip() and aka.strip().lower() != name.strip().lower():
                details += f"AKA: {aka}\n"
            details += f"Notes: {notes}\nCopperknob ID: {copperknob_id}\n"
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
            self.details_label.insert(tk.END, details)
            self.details_label.config(state='disabled')
        except Exception as e:
            debug_msg = f"Error loading details for id={db_id}: {e}"
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
