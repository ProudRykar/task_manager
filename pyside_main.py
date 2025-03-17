import sys
import psutil
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget, QPushButton, QMessageBox

class ProcessViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Process Viewer")
        self.setGeometry(100, 100, 900, 600)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        layout = QVBoxLayout()
        
        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["PID", "Name", "Memory Usage", "CPU Usage (%)"])
        self.tree.itemDoubleClicked.connect(self.show_process_info)
        layout.addWidget(self.tree)
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.populate_processes)
        layout.addWidget(self.refresh_button)
        
        self.central_widget.setLayout(layout)

        # Таймер для автообновления списка процессов
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.populate_processes)
        self.timer.start(2000)  # Обновление каждые 2 секунды

        self.populate_processes()
    
    def populate_processes(self):
        self.tree.clear()
        for proc in psutil.process_iter(attrs=['pid', 'name', 'memory_info', 'cpu_percent']):
            try:
                pid = proc.info['pid']
                name = proc.info['name']
                mem_usage = proc.info['memory_info'].rss / (1024 * 1024)  # Convert to MB
                cpu_usage = proc.info['cpu_percent']  # Get CPU usage

                item = QTreeWidgetItem([str(pid), name, f"{mem_usage:.2f} MB", f"{cpu_usage:.2f} %"])
                self.tree.addTopLevelItem(item)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    
    def show_process_info(self, item):
        pid = int(item.text(0))
        try:
            proc = psutil.Process(pid)
            info = (
                f"PID: {proc.pid}\n"
                f"Name: {proc.name()}\n"
                f"Executable: {proc.exe()}\n"
                f"Status: {proc.status()}\n"
                f"Memory Usage: {proc.memory_info().rss / (1024 * 1024):.2f} MB\n"
                f"CPU Usage: {proc.cpu_percent():.2f} %"
            )
            QMessageBox.information(self, "Process Info", info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            QMessageBox.warning(self, "Error", "Process no longer exists or access denied.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProcessViewer()
    window.show()
    sys.exit(app.exec())
