import sys
import signal
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QMessageBox, QDialog
from ui.add_dance_dialog import AddDanceDialog
from scrapers.dance_scraper import scrape_dance_info
from db.models import initialize_db, get_connection


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DanceDB")
        self.setGeometry(100, 100, 900, 600)
        # Layout with table and buttons
        central = QWidget()
        layout = QVBoxLayout()
        from PyQt5.QtGui import QPalette, QColor
        self.table = QTableWidget()
        # Make entire row select when any cell is clicked
        from PyQt5.QtWidgets import QAbstractItemView
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        # Set a more contrasted grid color using stylesheet for reliability
        self.table.setStyleSheet("QTableWidget { gridline-color: #B0B0B0; }")
        # Enable sorting and connect header click for custom toggle
        self.table.setSortingEnabled(True)
        self._last_sorted_col = None
        self._last_sort_order = None
        hdr = self.table.horizontalHeader()
        hdr.sectionClicked.connect(self.handle_header_clicked)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add Dance")
        self.add_btn.clicked.connect(self.open_add_dialog)
        btn_layout.addWidget(self.add_btn)
        self.edit_btn = QPushButton("Edit Selected")
        self.edit_btn.clicked.connect(self.edit_selected)
        btn_layout.addWidget(self.edit_btn)
        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.clicked.connect(self.delete_selected)
        btn_layout.addWidget(self.delete_btn)
        self.show_imported_btn = QPushButton("Batch Import")
        self.show_imported_btn.clicked.connect(self.open_imported_dances_dialog)
        btn_layout.addWidget(self.show_imported_btn)
        # Add Reset Sort button
        self.reset_sort_btn = QPushButton("Reset Sort")
        self.reset_sort_btn.clicked.connect(self.reset_sort)
        btn_layout.addWidget(self.reset_sort_btn)
        layout.addLayout(btn_layout)
        central.setLayout(layout)
        self.setCentralWidget(central)
        self.load_dances()
        # (Removed duplicate UI setup code)

    def reset_sort(self):
        # Disable sorting, reload data, and clear sort indicator
        self.table.setSortingEnabled(False)
        self.load_dances()
        hdr = self.table.horizontalHeader()
        hdr.setSortIndicator(-1, 0)
        self._last_sorted_col = None
        self._last_sort_order = None
        self.table.setSortingEnabled(True)

    def open_imported_dances_dialog(self):
        from ui.imported_dances_dialog import ImportedDancesDialog
        dlg = ImportedDancesDialog(self)
        dlg.exec_()

    def get_selected_row_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        # Get the dance name and choreographer to identify the row
        name = self.table.item(row, 0).text().strip() if self.table.item(row, 0) else None
        choreo = self.table.item(row, 9).text().strip() if self.table.item(row, 9) else None
        conn = get_connection()
        c = conn.cursor()
        # Try normal match
        c.execute("SELECT id FROM dances WHERE name=? AND (choreographer=? OR choreographer IS NULL OR choreographer='')", (name, choreo))
        result = c.fetchone()
        # Fallback: try matching by name only if not found
        if not result and name:
            c.execute("SELECT id FROM dances WHERE name=?", (name,))
            result = c.fetchone()
        conn.close()
        return result[0] if result else None

    def edit_selected(self):
        row_id = self.get_selected_row_id()
        if row_id is None:
            QMessageBox.warning(self, "No Selection", "Please select a dance to edit.")
            return
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT name, choreographer, release_date, level, count, wall, tag, restart, stepsheet_url, known_status, category, priority, action, notes FROM dances WHERE id=?", (row_id,))
        data = c.fetchone()
        conn.close()
        dialog = AddDanceDialog(parent=self)
        # Set dialog fields with data from the database
        dialog.name_input.setText(data[0])
        dialog.choreo_input.setText(data[1])
        if hasattr(dialog, 'release_date_input'):
            dialog.release_date_input.setText(data[2])
        dialog.level_input.setText(data[3])
        dialog.count_input.setText(data[4])
        dialog.wall_input.setText(data[5])
        dialog.tag_input.setText(data[6] or "")
        dialog.restart_input.setText(data[7] or "")
        dialog.url_input.setText(data[8])
        dialog.known_combo.setCurrentText(data[9] or "")
        dialog.category_combo.setCurrentText(data[10] or "")
        dialog.priority_combo.setCurrentText(data[11] or "")
        dialog.action_combo.setCurrentText(data[12] or "")
        dialog.notes_input.setPlainText(data[13] or "")
        if dialog.exec_():
            # Save changes
            conn = get_connection()
            c = conn.cursor()
            c.execute('''
                UPDATE dances SET name=?, choreographer=?, level=?, count=?, wall=?, tag=?, restart=?, stepsheet_url=?, known_status=?, category=?, priority=?, action=?, notes=? WHERE id=?
            ''', (
                dialog.name_input.text(),
                dialog.choreo_input.text(),
                dialog.level_input.text(),
                dialog.count_input.text(),
                dialog.wall_input.text(),
                dialog.tag_input.text(),
                dialog.restart_input.text(),
                dialog.url_input.text(),
                dialog.known_combo.currentText(),
                dialog.category_combo.currentText(),
                dialog.priority_combo.currentText(),
                dialog.action_combo.currentText(),
                dialog.notes_input.toPlainText(),
                row_id
            ))
            conn.commit()
            conn.close()
            self.load_dances()

    def delete_selected(self):
        row_id = self.get_selected_row_id()
        if row_id is None:
            QMessageBox.warning(self, "No Selection", "Please select a dance to delete.")
            return
        reply = QMessageBox.question(self, "Confirm Delete", "Are you sure you want to delete this dance?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            conn = get_connection()
            c = conn.cursor()
            c.execute("DELETE FROM dances WHERE id=?", (row_id,))
            conn.commit()
            conn.close()
            self.load_dances()

    def open_add_dialog(self):
        def fetch_callback(url, dialog):
            scraped = scrape_dance_info(url)
            if scraped:
                dialog.name_input.setText(scraped.get('dance_name', ''))
                choreos = scraped.get('choreographers', [])
                if isinstance(choreos, list):
                    choreo_str = ', '.join(
                        c['name'] for c in choreos if isinstance(c, dict)
                    )
                else:
                    choreo_str = str(choreos)
                dialog.choreo_input.setText(choreo_str)
                if hasattr(dialog, 'release_date_input'):
                    dialog.release_date_input.setText(scraped.get('release_date', ''))
                dialog.level_input.setText(scraped.get('level', ''))
                dialog.count_input.setText(scraped.get('count', ''))
                dialog.wall_input.setText(scraped.get('wall', ''))
                # Populate Songs field with all song info/switches
                if hasattr(dialog, 'songs_input'):
                    songs = scraped.get('songs', [])
                    if songs:
                        song_lines = [f"{s['title']} - {s['artist']}" if s['artist'] else s['title'] for s in songs]
                        dialog.songs_input.setPlainText('\n'.join(song_lines))
                    else:
                        dialog.songs_input.setPlainText('')
                dialog.notes_input.setPlainText(scraped.get('notes', ''))
        dialog = AddDanceDialog(fetch_callback=fetch_callback, parent=self)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            self.save_dance(dialog)

    def load_dances(self):
        from db.song_queries import get_songs_for_dance, get_dance_id_by_name_and_choreo
        # Preserve current sort state
        sort_col = self.table.horizontalHeader().sortIndicatorSection()
        sort_order = self.table.horizontalHeader().sortIndicatorOrder()
        sorting_enabled = self.table.isSortingEnabled()
        # Reset sort to unsorted before repopulating
        self.table.setSortingEnabled(False)
        self.table.horizontalHeader().setSortIndicator(-1, 0)

        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT name, choreographer, release_date, level, count, wall, tag, restart, known_status, category, priority, action FROM dances")
        rows = c.fetchall()
        headers = ["Name", "Songs", "Level", "Count", "Wall", "Known", "Category", "Priority", "Action", "Choreographer", "Release Date"]
        self.table.setRowCount(len(rows))
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        # Set wider columns for Name and Songs
        self.table.setColumnWidth(0, 200)  # Name
        self.table.setColumnWidth(1, 250)  # Songs
        self.table.setColumnWidth(3, 60)   # Count
        self.table.setColumnWidth(4, 60)   # Wall
        for row_idx, row in enumerate(rows):
            name = row[0]
            choreographer = row[1]
            release_date = row[2]
            level = row[3]
            count = row[4]
            wall = row[5]
            # Tag (6) and Restart (7) are skipped
            known = row[8]
            category = row[9]
            priority = row[10]
            action = row[11]
            # Songs (computed)
            dance_id = get_dance_id_by_name_and_choreo(name, choreographer)
            if dance_id:
                songs = get_songs_for_dance(dance_id)
                song_str = ", ".join(songs)
            else:
                song_str = ""
            # Build the row in the exact order of headers
            row_data = [
                name,           # Name
                song_str,       # Songs
                level,          # Level
                count,          # Count
                wall,           # Wall
                known,          # Known
                category,       # Category
                priority,       # Priority
                action,         # Action
                choreographer,  # Choreographer
                release_date    # Release Date
            ]
            for col_idx, value in enumerate(row_data):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))
        # Resize the 'Level' column to fit its contents
        level_col = headers.index("Level")
        self.table.resizeColumnToContents(level_col)
        conn.close()

        # Restore sorting if it was enabled
        self.table.setSortingEnabled(sorting_enabled)
        if sorting_enabled:
            self.table.sortItems(sort_col, sort_order)

    def load_dances(self):
        from db.song_queries import get_songs_for_dance, get_dance_id_by_name_and_choreo
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT name, choreographer, release_date, level, count, wall, tag, restart, known_status, category, priority, action FROM dances")
        rows = c.fetchall()
        headers = ["Name", "Songs", "Level", "Count", "Wall", "Known", "Category", "Priority", "Action", "Choreographer", "Release Date"]
        self.table.setRowCount(len(rows))
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        # Set wider columns for Name and Songs
        self.table.setColumnWidth(0, 200)  # Name
        self.table.setColumnWidth(1, 250)  # Songs
        self.table.setColumnWidth(3, 60)   # Count
        self.table.setColumnWidth(4, 60)   # Wall
        for row_idx, row in enumerate(rows):
            name = row[0]
            choreographer = row[1]
            release_date = row[2]
            level = row[3]
            dance_id = get_dance_id_by_name_and_choreo(name, choreographer)
            if dance_id:
                songs = get_songs_for_dance(dance_id)
                song_str = ", ".join(songs)
            else:
                song_str = ""
            # Insert name, songs, and level first
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(name)))
            self.table.setItem(row_idx, 1, QTableWidgetItem(song_str))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(level)))
            # Insert the rest of the columns, skipping Tag (6) and Restart (7), and moving choreographer/release_date to end
            rest = [row[4], row[5], row[8], row[9], row[10], row[11]]
            for col_idx, value in enumerate(rest, start=3):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))
            self.table.setItem(row_idx, 9, QTableWidgetItem(str(choreographer)))
            self.table.setItem(row_idx, 10, QTableWidgetItem(str(release_date)))
            # Resize the 'Level' column to fit its contents
            level_col = headers.index("Level")
            self.table.resizeColumnToContents(level_col)
        conn.close()

    def handle_header_clicked(self, logicalIndex):
        from PyQt5.QtCore import Qt
        # Toggle sort order if same column, else default to ascending
        if self._last_sorted_col == logicalIndex:
            order = Qt.DescendingOrder if self._last_sort_order == Qt.AscendingOrder else Qt.AscendingOrder
        else:
            order = Qt.AscendingOrder
        self.table.sortItems(logicalIndex, order)
        self._last_sorted_col = logicalIndex
        self._last_sort_order = order

if __name__ == "__main__":
    initialize_db()
    app = QApplication(sys.argv)
    # Allow Ctrl+C to close the app
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
