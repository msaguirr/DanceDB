import tkinter as tk
from tkinter import ttk, messagebox
import tksheet
import sqlite3
import os

DB_PATH = os.path.join(os.path.expanduser("~"), "dances.db")

class SheetView(ttk.Frame):
    def __init__(self, parent, headers, on_row_selected, *args, **kwargs):
        self._sort_state = {}  # column index -> ascending bool
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
        #self.sheet.select_row(1, redraw=True)
        self.sheet.enable_bindings("all")
        #self.sheet.extra_bindings([("cell_select", self.on_cell_select)])
        
        #self.sheet.single_selection_enabled = False
        #self.sheet.set_options(show_selected_cells_border=False)

        self.sheet.extra_bindings([
            ("row_select", self._on_sheet_row_select),
            ("cell_select", self._on_cell_select),
            ("header_select", self._on_header_select_debug),
            ("column_select", self._on_column_select_debug)
        ])

    def _on_header_select_debug(self, event):
        print("[DEBUG] header_select event:", event)
        return None

    def _on_column_select_debug(self, event):
        print("[DEBUG] column_select event:", event)
        sel = event.get('selected', None)
        col = None
        if sel is not None and hasattr(sel, 'column'):
            col = sel.column
        # Fallback: try to get from selection_boxes
        if col is None and 'selection_boxes' in event:
            boxes = event['selection_boxes']
            for box, typ in boxes.items():
                if typ == 'columns' and hasattr(box, 'from_c'):
                    col = box.from_c
                    break
        if col is not None:
            # Toggle sort direction for this column
            ascending = self._sort_state.get(col, True)
            self._sort_state[col] = not ascending
            print(f"[DEBUG] Manual sorting column {col} | ascending={ascending}")
            # Print all rows before sort
            print("[DEBUG] All rows before sort:")
            for i, row in enumerate(self._current_data):
                print(f"  Row {i}: {row}")
            # Sort self._current_data and self._row_id_map together
            combined = list(zip(self._current_data, self._row_id_map))
            combined.sort(key=lambda x: (x[0][col] or '').lower(), reverse=not ascending)
            if combined:
                self._current_data, self._row_id_map = zip(*combined)
                self._current_data = list(self._current_data)
                self._row_id_map = list(self._row_id_map)
            else:
                self._current_data, self._row_id_map = [], []
            self.sheet.set_sheet_data(self._current_data, reset_col_positions=True, reset_row_positions=True)
            self.sheet.set_all_cell_sizes_to_text()
            self.sheet.redraw()
            # Print all rows after sort
            print("[DEBUG] All rows after manual sort:")
            for i, row in enumerate(self._current_data):
                print(f"  Row {i}: {row}")
        return None
        # Debug: print all attributes of the Sheet object to find header widget
        print("[DEBUG] tksheet.Sheet attributes:", dir(self.sheet))

    def _on_header_left_click_sort(self, event):
        # Determine which column was clicked
        x = event.x
        col = self.sheet.get_col_at_pos(x)
        print(f"[DEBUG] Header left-clicked: column {col}")
        if col is not None:
            self.sheet.sort_column(col)

    def _on_column_header_click_debug(self, event):
        print("[DEBUG] column_header_click event:", event)
        col = event.get('column', None)
        print(f"[DEBUG] Clicked column index: {col}")
        # Let tksheet handle the sort as normal
        return None
        self.sheet.bind("<<SheetModified>>", self._on_sheet_modified)

    def _on_sheet_modified(self, event):
        # Called after a sort or other modification
        # Print event for debug
        print("[DEBUG] <<SheetModified>> event:", event)
        # If the event is a sort, update row_id_map to match new order
        # (tksheet does not update your external row_id_map automatically)
        # You may need to update self._row_id_map here if you rely on it
        # For now, just print a message
        # You can add logic here to sync row_id_map if needed
        pass

    # (debug event wrapper removed)

    # Removed custom _on_column_select; tksheet built-in sort will be used


    # (removed duplicate/unused on_cell_select)
        
    # Bind the function to the CellSelect event
    #self.sheet.extra_bindings([("cell_select", on_cell_select)])

    def _on_cell_select(self, event):
        print("[DEBUG] cell_select event:", event)
        row_idx = self.get_selected_row_idx()
        if event.get('type') == 'header':
            print("[DEBUG] cell_select: header clicked")
            self.sheet.deselect('all')
            self.sheet.deselect('cells')
            self.sheet.deselect('rows')
            if self.on_row_selected:
                self.on_row_selected(None)
            return "break"
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

    def set_data(self, data, row_id_map):
        # Debug: print data types for each column in the first few rows
        if data:
            print("[DEBUG] set_data: first 3 rows and their types:")
            for i, row in enumerate(data[:3]):
                print(f"  Row {i}: {[type(cell) for cell in row]} | {row}")
        self._current_data = list(data)
        self._row_id_map = list(row_id_map)
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
        print("[DEBUG] row_select event:", event)
        row_idx = self.get_selected_row_idx()
        if event.get('type') == 'header':
            print("[DEBUG] row_select: header clicked")
            self.sheet.deselect('all')
            self.sheet.deselect('cells')
            self.sheet.deselect('rows')
            if self.on_row_selected:
                self.on_row_selected(None)
            return "break"
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
    import tksheet
    print("[DEBUG] tksheet version:", tksheet.__version__)
    app = DanceDBViewer()
    app.mainloop()
