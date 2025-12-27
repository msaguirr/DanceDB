from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox, QLabel, QScrollArea, QWidget, QListWidget, QListWidgetItem, QLineEdit, QTextEdit, QComboBox, QSizePolicy
import csv

CSV_PATH = 'assets/copperknob_links_and_songs.csv'

class ImportedDancesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Imported Dances")
        self.setFixedSize(1000, 900)
        self.move(100, 100)

        main_layout = QHBoxLayout()

        # Left panel: checkboxes and controls
        left_layout = QVBoxLayout()
        self.count_label = QLabel()
        left_layout.addWidget(self.count_label)
        self.checkboxes = []
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        vbox = QVBoxLayout()
        self.dance_rows = []  # Store CSV rows for later reference
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            for row in reader:
                if len(row) >= 2:
                    cb = QCheckBox(f"{row[1]} (Song: {row[2]})")
                    cb.setChecked(True)
                    cb.stateChanged.connect(self.update_count)
                    self.checkboxes.append(cb)
                    vbox.addWidget(cb)
                    self.dance_rows.append(row)
        container.setLayout(vbox)
        scroll.setWidget(container)
        left_layout.addWidget(scroll)

        btns = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        deselect_all_btn = QPushButton("Deselect All")
        fetch_selected_btn = QPushButton("Fetch Selected")
        select_all_btn.clicked.connect(self.select_all)
        deselect_all_btn.clicked.connect(self.deselect_all)
        fetch_selected_btn.clicked.connect(self.fetch_selected)
        btns.addWidget(select_all_btn)
        btns.addWidget(deselect_all_btn)
        btns.addWidget(fetch_selected_btn)
        left_layout.addLayout(btns)

        # Right panel: list of fetched dances and details
        right_layout = QVBoxLayout()
        self.fetched_list = QListWidget()
        self.fetched_list.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.fetched_list.currentRowChanged.connect(self.show_fetched_details)
        right_layout.addWidget(QLabel("Fetched Dances:"))
        right_layout.addWidget(self.fetched_list)

        # Details area (read-only, mimics AddDanceDialog)
        self.details_widget = QWidget()
        details_layout = QVBoxLayout()
        self.details_widget.setLayout(details_layout)
        self.detail_fields = {}
        field_defs = [
            ("Dance Name", QLineEdit, 'name'),
            ("Choreographer(s)", QLineEdit, 'choreographers'),
            ("Release Date", QLineEdit, 'release_date'),
            ("Level", QLineEdit, 'level'),
            ("Count", QLineEdit, 'count'),
            ("Wall", QLineEdit, 'wall'),
            ("Songs", QTextEdit, 'songs'),
            ("Known Status", QLineEdit, 'known_status'),
            ("Category", QLineEdit, 'category'),
            ("Priority", QLineEdit, 'priority'),
            ("Action", QLineEdit, 'action'),
        ]
        for label, widget_cls, key in field_defs:
            l = QLabel(label + ":")
            field = widget_cls()
            if isinstance(field, QLineEdit):
                field.setReadOnly(True)
            elif isinstance(field, QTextEdit):
                field.setReadOnly(True)
                field.setMaximumHeight(60)
            details_layout.addWidget(l)
            details_layout.addWidget(field)
            self.detail_fields[key] = field
        self.details_widget.setVisible(False)
        right_layout.addWidget(self.details_widget)

        main_layout.addLayout(left_layout, 2)
        main_layout.addLayout(right_layout, 3)
        self.setLayout(main_layout)
        self.update_count()

        # Store fetched data: list of dicts
        self.fetched_dances = []

    def fetch_selected(self):
        from PyQt5.QtWidgets import QMessageBox
        import requests
        from scrapers.dance_scraper import scrape_dance_info
        self.fetched_dances = []
        self.fetched_list.clear()
        for cb, row in zip(self.checkboxes, self.dance_rows):
            if cb.isChecked():
                url = row[0]
                info = scrape_dance_info(url)
                if info:
                    self.fetched_dances.append(info)
                    display_name = info.get('name', '') or row[1]
                    choreo = info.get('choreographer', '').strip()
                    if choreo:
                        self.fetched_list.addItem(f"{display_name} (Choreo: {choreo})")
                    else:
                        self.fetched_list.addItem(display_name)
                else:
                    self.fetched_dances.append(None)
                    self.fetched_list.addItem(f"Failed to fetch: {url}")
        if self.fetched_dances:
            self.details_widget.setVisible(True)
            self.fetched_list.setCurrentRow(0)
        else:
            self.details_widget.setVisible(False)
            QMessageBox.information(self, "Fetch Results", "No dances selected or fetched.")

    def show_fetched_details(self, row):
        if row < 0 or row >= len(self.fetched_dances):
            for field in self.detail_fields.values():
                if isinstance(field, QLineEdit):
                    field.clear()
                elif isinstance(field, QTextEdit):
                    field.clear()
            return
        info = self.fetched_dances[row]
        if not info:
            for field in self.detail_fields.values():
                if isinstance(field, QLineEdit):
                    field.setText("Failed to fetch")
                elif isinstance(field, QTextEdit):
                    field.setPlainText("")
            return
        # Set all fields from info dict
        # Dance Name: try 'dance_name', fallback to 'name' or 'title'
        dance_name = info.get('dance_name') or info.get('name') or info.get('title', '')
        self.detail_fields['name'].setText(dance_name)
        # Choreographer(s): join names if list, fallback to string
        choreos = info.get('choreographers')
        if isinstance(choreos, list):
            names = ', '.join(c.get('name', '') for c in choreos if isinstance(c, dict))
            self.detail_fields['choreographers'].setText(names)
        else:
            self.detail_fields['choreographers'].setText(str(choreos) if choreos else info.get('choreographer', ''))
        self.detail_fields['release_date'].setText(info.get('release_date', ''))
        self.detail_fields['level'].setText(info.get('level', ''))
        self.detail_fields['count'].setText(info.get('count', ''))
        self.detail_fields['wall'].setText(info.get('wall', ''))
        # Songs: join list if present
        songs = info.get('songs', [])
        if isinstance(songs, list):
            song_lines = [f"{s['title']} - {s['artist']}" if s.get('artist') else s.get('title', '') for s in songs]
            self.detail_fields['songs'].setPlainText('\n'.join(song_lines))
        else:
            self.detail_fields['songs'].setPlainText(str(songs))
        self.detail_fields['known_status'].setText(info.get('known_status', ''))
        self.detail_fields['category'].setText(info.get('category', ''))
        self.detail_fields['priority'].setText(info.get('priority', ''))
        self.detail_fields['action'].setText(info.get('action', ''))

    def select_all(self):
        for cb in self.checkboxes:
            cb.setChecked(True)
        self.update_count()

    def deselect_all(self):
        for cb in self.checkboxes:
            cb.setChecked(False)
        self.update_count()

    def update_count(self):
        selected = sum(cb.isChecked() for cb in self.checkboxes)
        total = len(self.checkboxes)
        self.count_label.setText(f"Selected: {selected} / {total}")
