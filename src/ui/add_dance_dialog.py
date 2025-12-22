from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QTextEdit

class AddDanceDialog(QDialog):
    def __init__(self, fetch_callback=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Dance")
        self.fetch_callback = fetch_callback
        layout = QVBoxLayout()

        # Stepsheet URL
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("Stepsheet URL:"))
        self.url_input = QLineEdit()
        url_layout.addWidget(self.url_input)
        self.fetch_btn = QPushButton("Fetch Info")
        url_layout.addWidget(self.fetch_btn)
        layout.addLayout(url_layout)

        # Name
        layout.addWidget(QLabel("Dance Name:"))
        self.name_input = QLineEdit()
        layout.addWidget(self.name_input)

        # Choreographer
        layout.addWidget(QLabel("Choreographer:"))
        self.choreo_input = QLineEdit()
        layout.addWidget(self.choreo_input)

        # Level
        layout.addWidget(QLabel("Level:"))
        self.level_input = QLineEdit()
        layout.addWidget(self.level_input)

        # Count
        layout.addWidget(QLabel("Count:"))
        self.count_input = QLineEdit()
        layout.addWidget(self.count_input)

        # Wall
        layout.addWidget(QLabel("Wall:"))
        self.wall_input = QLineEdit()
        layout.addWidget(self.wall_input)

        # Known Status
        layout.addWidget(QLabel("Known Status:"))
        self.known_combo = QComboBox()
        self.known_combo.addItems(["", "Yes", "Kinda", "No", "On the Floor"])
        layout.addWidget(self.known_combo)

        # Category
        layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(["", "Learn Next", "Learn Soon", "Learn Later", "Uncategorized"])
        layout.addWidget(self.category_combo)

        # Priority
        layout.addWidget(QLabel("Priority:"))
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["", "High", "Medium", "Low"])
        layout.addWidget(self.priority_combo)

        # Action
        layout.addWidget(QLabel("Action:"))
        self.action_combo = QComboBox()
        self.action_combo.addItems(["", "Learn", "Practice"])
        layout.addWidget(self.action_combo)

        # Notes
        layout.addWidget(QLabel("Notes:"))
        self.notes_input = QTextEdit()
        layout.addWidget(self.notes_input)

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # Connect fetch button
        if self.fetch_callback:
            self.fetch_btn.clicked.connect(lambda: self.fetch_callback(self.url_input.text(), self))

        # Connect Save and Cancel buttons
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
