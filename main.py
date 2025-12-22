import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidget, QTableWidgetItem
from db.models import initialize_db, get_connection

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DanceDB")
        self.setGeometry(100, 100, 900, 600)
        self.table = QTableWidget()
        self.setCentralWidget(self.table)
        self.load_dances()

    def load_dances(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT name, choreographer, level, known_status, category, priority, action FROM dances")
        rows = c.fetchall()
        headers = ["Name", "Choreographer", "Level", "Known", "Category", "Priority", "Action"]
        self.table.setRowCount(len(rows))
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        for row_idx, row in enumerate(rows):
            for col_idx, value in enumerate(row):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))
        conn.close()

if __name__ == "__main__":
    initialize_db()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
