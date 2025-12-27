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
		self.table.setAlternatingRowColors(True)
		self.table.setShowGrid(True)
		# Set a more contrasted grid color using stylesheet for reliability
		self.table.setStyleSheet("QTableWidget { gridline-color: #B0B0B0; }")
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
		layout.addLayout(btn_layout)
		central.setLayout(layout)
		self.setCentralWidget(central)
		self.load_dances()

	def open_imported_dances_dialog(self):
		from ui.imported_dances_dialog import ImportedDancesDialog
		dlg = ImportedDancesDialog(self)
		dlg.exec_()
	def get_selected_row_id(self):
		row = self.table.currentRow()
		if row < 0:
			return None
		# Get the dance name and choreographer to identify the row
		name = self.table.item(row, 0).text() if self.table.item(row, 0) else None
		choreo = self.table.item(row, 1).text() if self.table.item(row, 1) else None
		conn = get_connection()
		c = conn.cursor()
		c.execute("SELECT id FROM dances WHERE name=? AND choreographer=?", (name, choreo))
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
		if not data:
			QMessageBox.warning(self, "Not Found", "Selected dance not found in database.")
			return
		def fetch_callback(url, dialog):
			from scrapers.dance_scraper import scrape_dance_info
			scraped = scrape_dance_info(url)
			if scraped:
				dialog.name_input.setText(scraped.get('dance_name', ''))
				# Format choreographers list for display (just names, no countries)
				choreos = scraped.get('choreographers', [])
				if isinstance(choreos, list):
					names = []
					for c in choreos:
						if isinstance(c, dict):
							name = c.get('name', '')
							if name and name.strip():
								names.append(name.strip())
					choreo_str = ', '.join(names)
				else:
					choreo_str = str(choreos).strip()
				dialog.choreo_input.setText(choreo_str)

				# Set release date if present
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
		from ui.add_dance_dialog import AddDanceDialog
		dialog = AddDanceDialog(fetch_callback=fetch_callback, parent=self)
		dialog.name_input.setText(data[0])
		dialog.choreo_input.setText(data[1])
		if hasattr(dialog, 'release_date_input'):
			dialog.release_date_input.setText(data[2] or "")
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

	def save_dance(self, dialog):
		name = dialog.name_input.text()
		choreo = dialog.choreo_input.text()
		release_date = dialog.release_date_input.text() if hasattr(dialog, 'release_date_input') else ''
		level = dialog.level_input.text()
		count = dialog.count_input.text()
		wall = dialog.wall_input.text()
		tag = dialog.tag_input.text()
		restart = dialog.restart_input.text()
		url = dialog.url_input.text()
		known = dialog.known_combo.currentText()
		category = dialog.category_combo.currentText()
		priority = dialog.priority_combo.currentText()
		action = dialog.action_combo.currentText()
		notes = dialog.notes_input.toPlainText()
		from PyQt5.QtWidgets import QMessageBox
		if not name.strip():
			QMessageBox.warning(dialog, "Missing Name", "Dance name is required.")
			return
		try:
			conn = get_connection()
			c = conn.cursor()
			c.execute('''
				INSERT INTO dances (name, choreographer, release_date, level, count, wall, tag, restart, stepsheet_url, known_status, category, priority, action, notes)
				VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
			''', (
				name, choreo, release_date, level, count, wall, tag, restart, url, known, category, priority, action, notes
			))
			conn.commit()
			conn.close()
			self.load_dances()
		except Exception as e:
			QMessageBox.critical(dialog, "Error", f"Failed to save dance: {e}")

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
		conn.close()

if __name__ == "__main__":
	initialize_db()
	app = QApplication(sys.argv)
	# Allow Ctrl+C to close the app
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	window = MainWindow()
	window.show()
	sys.exit(app.exec_())
