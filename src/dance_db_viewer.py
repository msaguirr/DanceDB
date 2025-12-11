import tkinter as tk
from tkinter import ttk, messagebox
import tksheet
import sqlite3
import os

DB_PATH = os.path.join(os.path.expanduser("~"), "dances.db")

class SheetView(ttk.Frame):
    def __init__(self, parent, headers, on_row_selected, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.on_row_selected = on_row_selected  # callback: row_idx -> None
        self.sheet = tksheet.Sheet(self,
            headers=headers,
            show_row_index=False,
            show_header=True,
            width=800,
            row_height=60,
            align="w",
            enable_edit=False,
            theme="dark",
            table_bg="#242424",
            header_bg="#2F2E2E",
            table_wrap=""
        )
        self.sheet.grid(row=0, column=0, sticky="nsew")
        self.sheet.config(width=800)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._row_id_map = []
        self.sheet.enable_bindings(("single_select", "row_select", "rc_select", "arrowkeys"))
        self.sheet.extra_bindings([
            ("row_select", self._on_sheet_row_select),
            ("cell_select", self._on_sheet_row_select)
        ])

    def set_data(self, data, row_id_map):
        self._row_id_map = row_id_map
        self.sheet.set_sheet_data(data, reset_col_positions=True, reset_row_positions=True)
        self.sheet.set_all_cell_sizes_to_text()

    def get_selected_row_idx(self):
        selected = self.sheet.get_selected_rows()
        if selected:
            return list(selected)[0]
        selected_cells = self.sheet.get_selected_cells()
        if selected_cells:
            return list(selected_cells)[0][0]
        return None

    def deselect_all(self):
        self.sheet.deselect('all')
        self.sheet.deselect('cells')

    def _on_sheet_row_select(self, event):
        row_idx = self.get_selected_row_idx()
        if row_idx is not None:
            if list(self.sheet.get_selected_rows()) != [row_idx]:
                self.sheet.deselect('all')
                self.sheet.select_row(row_idx)
            self.sheet.deselect('cells')
            if self.on_row_selected:
                self.on_row_selected(row_idx)
        else:
            self.deselect_all()
            if self.on_row_selected:
                self.on_row_selected(None)
        return "break"


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
        self.geometry("1200x550")
        self.search_var = tk.StringVar()
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        import tkinter.font as tkfont
        tree_font = tkfont.nametofont("TkDefaultFont")

        main_frame = ttk.Frame(self)
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=0)
        main_frame.rowconfigure(0, weight=0)
        main_frame.rowconfigure(1, weight=1)

        search_frame = ttk.Frame(main_frame)
        search_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=6)
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        search_entry.pack(side=tk.LEFT, padx=4)
        ttk.Button(search_frame, text="Search", command=self._load_data).pack(side=tk.LEFT, padx=8)
        search_entry.bind('<Return>', lambda e: self._load_data())
        ttk.Button(search_frame, text="Delete Selected", command=self._delete_selected_row).pack(side=tk.LEFT, padx=8)

        left_frame = ttk.Frame(main_frame, width=800)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(0,8), pady=0)
        left_frame.grid_propagate(False)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)

        right_frame = ttk.Frame(main_frame, width=340)
        right_frame.grid(row=1, column=1, sticky="ns", padx=(0,0), pady=0)
        right_frame.grid_propagate(False)

        # --- SheetView setup ---
        self.sheet_view = SheetView(left_frame,
            headers=["Name", "Songs", "Level", "Priority", "Category"],
            on_row_selected=self._on_sheet_row_selected
        )
        self.sheet_view.grid(row=0, column=0, sticky="nsew")
        left_frame.rowconfigure(0, weight=1)
        left_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)
        right_frame.columnconfigure(0, weight=1)

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

        self.notification_label = ttk.Label(self, text="", foreground="green", font=tree_font)
        self.notification_label.grid(row=1, column=0, sticky="ew", padx=8, pady=4)
        
    def _delete_selected_row(self):
        selected = self.sheet.get_selected_rows()
        if not selected:
            messagebox.showwarning("Delete", "No row selected.")
            return
        row_idx = selected[0]
        # Get dance name for confirmation
        dance_name = self.sheet.get_cell_data(row_idx, 0) or "this dance"
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
            # TODO: Implement actual delete logic for tksheet (update DB and reload)
            self._actually_delete_row(row_idx)
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
        # Actual DB delete logic will be handled in _actually_delete_row (to be updated)

    def _load_data(self):
        search_filter = self.search_var.get().strip().lower()
        data = []
        row_id_map = []
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            query = "SELECT id, name, level, choreographers, release_date, priority, category, frequency, aka, notes, copperknob_id, songs FROM dances ORDER BY name"
            for row in c.execute(query):
                (db_id, name, level, choreographers, release_date, priority, category, frequency, aka, notes, copperknob_id, songs_json) = row
                match = True
                if search_filter:
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
                    try:
                        import json
                        songs = json.loads(songs_json)
                        song_lines = [f"{s.get('song_name','')} by {s.get('artist','')}" for s in songs if s.get('song_name') or s.get('artist')]
                        song_display = "\n".join(song_lines)
                    except Exception:
                        song_display = ""
                    data.append([name, song_display, level, priority, category])
                    row_id_map.append(db_id)
            conn.close()
            self.sheet_view.set_data(data, row_id_map)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data: {e}")

    def _on_sheet_row_selected(self, row_idx):
        # Called by SheetView when a row is selected (row_idx or None)
        if row_idx is None:
            self.details_label.config(state='normal')
            self.details_label.delete('1.0', tk.END)
            self.details_label.config(state='disabled')
            self.geometry("900x550")
            return
        # Get row_id_map from SheetView
        if not hasattr(self.sheet_view, '_row_id_map') or row_idx >= len(self.sheet_view._row_id_map):
            return
        db_id = self.sheet_view._row_id_map[row_idx]
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

    # Double-click handler for Treeview is obsolete and removed.

if __name__ == "__main__":
    app = DanceDBViewer()
    app.mainloop()
