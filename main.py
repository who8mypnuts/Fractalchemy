import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtUiTools import QUiLoader

def main():
    app = QApplication(sys.argv)
    loader = QUiLoader()
    window = loader.load("ui/main_window.ui")
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()