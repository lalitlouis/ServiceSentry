import rumps
import psutil
from AppKit import NSWorkspace, NSAlert, NSApplication, NSApp, NSAppearance
import datetime
import subprocess
import json
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt5.QtGui import QPainter, QColor, QFont
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTableWidget, QTableWidgetItem, QPushButton, 
                             QHeaderView, QCheckBox)
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTableWidget, QTableWidgetItem, QPushButton, 
                             QHeaderView, QCheckBox, QLineEdit, QStyle)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QBrush

def show_alert(title, message):
    NSApp.activateIgnoringOtherApps_(True)
    
    alert = NSAlert.alloc().init()
    alert.setMessageText_(title)
    alert.setInformativeText_(message)
    alert.addButtonWithTitle_("OK")
    alert.runModal()

class ChromeTabPopup(QWidget):
    def __init__(self, tabs):
        super().__init__()
        self.tabs = tabs
        self.initUI()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time_spent)
        self.timer.start(1000)  # Update every second

    def initUI(self):
        self.setWindowTitle('Chrome Tabs Manager')
        self.setGeometry(100, 100, 1000, 600)

        layout = QVBoxLayout()

        # Buttons layout
        button_layout = QHBoxLayout()
        self.close_button = QPushButton('Close Selected Tabs')
        self.close_button.clicked.connect(self.close_selected_tabs)
        self.refresh_button = QPushButton('Refresh')
        self.refresh_button.clicked.connect(self.refresh_tabs)
        button_layout.addWidget(self.close_button)
        button_layout.addWidget(self.refresh_button)
        layout.addLayout(button_layout)

        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText('Search tabs...')
        self.search_bar.textChanged.connect(self.filter_tabs)
        layout.addWidget(self.search_bar)

        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(['', 'Title', 'URL', 'CPU Usage', 'Memory Usage', 'Visit Count', 'Time Spent'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #f0f0f0;
                alternate-background-color: #e0e0e0;
            }
            QHeaderView::section {
                background-color: #d0d0d0;
                padding: 4px;
                border: 1px solid #c0c0c0;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 4px;
            }
        """)

        layout.addWidget(self.table)
        self.setLayout(layout)
        self.populate_table()
        self.show()

    def populate_table(self):
        self.table.setRowCount(len(self.tabs))
        for i, tab in enumerate(self.tabs):
            checkbox = QCheckBox()
            self.table.setCellWidget(i, 0, checkbox)
            self.table.setItem(i, 1, QTableWidgetItem(tab['title']))
            self.table.setItem(i, 2, QTableWidgetItem(tab['url']))
            self.table.setItem(i, 3, QTableWidgetItem(f"{tab['cpu']:.2f}%"))
            self.table.setItem(i, 4, QTableWidgetItem(f"{tab['memory']:.2f}%"))
            self.table.setItem(i, 5, QTableWidgetItem(str(tab.get('visit_count', 0))))
            self.table.setItem(i, 6, QTableWidgetItem(self.format_time(tab.get('time_spent', 0))))

    def close_selected_tabs(self):
        selected_indices = []
        for i in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(i, 0)
            if checkbox.isChecked():
                selected_indices.append(i)

        for index in reversed(selected_indices):
            self.close_tab(index)

        self.populate_table()

    def close_tab(self, index):
        tab = self.tabs[index]
        try:
            subprocess.run([
                "osascript",
                "-e", f'tell application "Google Chrome"',
                "-e", f'set targetTab to tab "{tab["title"]}" of window 1',
                "-e", f'close targetTab',
                "-e", f'end tell'
            ], check=True)
            del self.tabs[index]
        except subprocess.CalledProcessError:
            print(f"Failed to close tab: {tab['title']}")

    def refresh_tabs(self):
        # Here you would add code to refresh the tab information from Chrome
        # For now, we'll just update the CPU and memory usage
        for tab in self.tabs:
            tab['cpu'] = psutil.cpu_percent(interval=0.1) / len(self.tabs)
            tab['memory'] = psutil.virtual_memory().percent / len(self.tabs)
        self.populate_table()

    def filter_tabs(self):
        search_text = self.search_bar.text().lower()
        for row in range(self.table.rowCount()):
            match = False
            for col in range(1, 3):  # Search in title and URL columns
                item = self.table.item(row, col)
                if item and search_text in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match)

    def update_time_spent(self):
        for tab in self.tabs:
            tab['time_spent'] = tab.get('time_spent', 0) + 1
        self.populate_table()

    @staticmethod
    def format_time(seconds):
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

class ServiceSentry(rumps.App):
    def __init__(self):
        super(ServiceSentry, self).__init__("ServiceSentry")
        self.menu = ["System Overview", "Process Details", "Quit"]
        self.current_app = None
        self.initialize_nsapp()
        
    def initialize_nsapp(self):
        NSApplication.sharedApplication()
        NSApp.setActivationPolicy_(1)
        NSApp.setAppearance_(NSAppearance.appearanceNamed_("NSAppearanceNameDarkAqua"))

    @rumps.timer(1)
    def update_status(self, _):
        active_app = self.get_active_app()
        if active_app != self.current_app:
            self.current_app = active_app

        cpu_usage, memory_usage, memory_percent = self.get_resource_usage(active_app)
        
        self.title = f"{active_app[:10]}: CPU {cpu_usage:.1f}% Mem {memory_percent:.1f}%"
        
        tooltip = (f"CPU: {cpu_usage:.1f}% ({psutil.cpu_count()} cores)\n"
                   f"Memory: {memory_usage:.1f}MB / {psutil.virtual_memory().total / (1024**2):.1f}MB "
                   f"({memory_percent:.1f}%)")
        self.menu.title = tooltip

    def get_active_app(self):
        active_app = NSWorkspace.sharedWorkspace().activeApplication()
        return active_app['NSApplicationName']

    def get_resource_usage(self, app_name):
        try:
            for proc in psutil.process_iter(['name', 'cpu_percent', 'memory_info', 'memory_percent']):
                if proc.info['name'] == app_name:
                    cpu_usage = proc.info['cpu_percent']
                    memory_usage = proc.info['memory_info'].rss / 1024 / 1024
                    memory_percent = proc.info['memory_percent']
                    return cpu_usage, memory_usage, memory_percent
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
        return 0.0, 0.0, 0.0

    @rumps.clicked("System Overview")
    def show_system_overview(self, _):
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        overview = (f"CPU Usage: {cpu_percent:.1f}%\n"
                    f"Memory Usage: {memory.percent:.1f}%\n"
                    f"Disk Usage: {disk.percent:.1f}%\n"
                    f"Available Disk: {disk.free / (1024**3):.2f} GB")
        
        show_alert("System Overview", overview)

    @rumps.clicked("Process Details")
    def show_process_details(self, _):
        if not self.current_app:
            show_alert("Error", "No active app detected")
            return

        if self.current_app == "Google Chrome":
            self.show_chrome_tabs()
        else:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'create_time']):
                if proc.info['name'] == self.current_app:
                    create_time = datetime.datetime.fromtimestamp(proc.info['create_time'])
                    details = (f"Name: {self.current_app}\n"
                               f"PID: {proc.info['pid']}\n"
                               f"CPU Usage: {proc.info['cpu_percent']:.1f}%\n"
                               f"Memory Usage: {proc.info['memory_percent']:.2f}%\n"
                               f"Started: {create_time:%Y-%m-%d %H:%M:%S}")
                    
                    show_alert("Process Details", details)
                    return

            show_alert("Error", "Process not found")

    def show_chrome_tabs(self):
        try:
            result = subprocess.run([
                "osascript",
                "-e", 'tell application "Google Chrome"',
                "-e", 'set tabList to {}',
                "-e", 'repeat with w in windows',
                "-e", '    repeat with t in tabs of w',
                "-e", '        set end of tabList to {title:title of t, url:URL of t}',
                "-e", '    end repeat',
                "-e", 'end repeat',
                "-e", 'return tabList',
                "-e", 'end tell'
            ], capture_output=True, text=True)

            if result.returncode != 0:
                raise Exception(f"AppleScript failed with return code {result.returncode}")

            # Parse the custom format
            raw_data = result.stdout.strip()
            tab_data = raw_data.split(", name:")
            tabs = []
            for item in tab_data:
                parts = item.split(", URL:")
                if len(parts) == 2:
                    title = parts[0].replace("name:", "").strip()
                    url = parts[1].strip()
                    tabs.append({
                        'title': title, 
                        'url': url, 
                        'cpu': psutil.cpu_percent(interval=0.1) / len(tab_data),
                        'memory': psutil.virtual_memory().percent / len(tab_data),
                        'visit_count': 1,  # This should be retrieved from Chrome's history if possible
                        'time_spent': 0
                    })

            app = QApplication([])
            ex = ChromeTabPopup(tabs)
            app.exec_()

        except Exception as e:
            show_alert("Error", f"Failed to get Chrome tabs: {str(e)}")

if __name__ == "__main__":
    app = ServiceSentry()
    app.run()