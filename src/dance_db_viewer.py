import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import os

DB_PATH = os.path.join(os.path.expanduser("~"), "dances.db")

class DanceDBViewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DanceDB Viewer")
        self.geometry("900x500")
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        self.tree = ttk.Treeview(self, columns=("name", "level", "choreographers", "release_date", "priority", "category", "frequency"), show="headings")
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col.title())
            self.tree.column(col, width=120, anchor=tk.W)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<Double-1>", self._on_row_double_click)

    def _load_data(self):
        self.tree.delete(*self.tree.get_children())
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT name, level, choreographers, release_date, priority, category, frequency FROM dances ORDER BY name")
            for row in c.fetchall():
                self.tree.insert("", tk.END, values=row)
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data: {e}")

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
