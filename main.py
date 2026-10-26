import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtUiTools import QUiLoader

def main():
    app = QApplication(sys.argv)
    loader = QUiLoader()
    window = loader.load("ui/main_window.ui")
    menubar = window.menuBar()
    window.setMenuBar(menubar)
    menubar.setVisible(True)
    status = window.statusBar()
    status.setVisible(True)
    window.setStatusBar(status)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()