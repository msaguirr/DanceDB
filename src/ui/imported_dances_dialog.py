from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox, QLabel, QScrollArea, QWidget
import csv

CSV_PATH = 'assets/copperknob_links_and_songs.csv'

class ImportedDancesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Imported Dances")
        self.resize(500, 600)
        layout = QVBoxLayout()

        # Count label
        self.count_label = QLabel()
        layout.addWidget(self.count_label)

        # Load dances from CSV
        self.checkboxes = []
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        vbox = QVBoxLayout()
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
        container.setLayout(vbox)
        scroll.setWidget(container)
        layout.addWidget(scroll)

        btns = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        deselect_all_btn = QPushButton("Deselect All")
        select_all_btn.clicked.connect(self.select_all)
        deselect_all_btn.clicked.connect(self.deselect_all)
        btns.addWidget(select_all_btn)
        btns.addWidget(deselect_all_btn)
        layout.addLayout(btns)

        self.setLayout(layout)
        self.update_count()

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
