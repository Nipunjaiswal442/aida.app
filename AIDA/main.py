import warnings
warnings.filterwarnings("ignore")

import sys
import os

# Ensure Homebrew and local binaries are in the PATH (fixes 'ffmpeg' not found when launched via Automator)
os.environ["PATH"] += os.pathsep + "/opt/homebrew/bin" + os.pathsep + "/usr/local/bin"

from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)

    # Create and show MainWindow
    window = MainWindow()
    window.show()

    # Trigger startup greeting automatically
    window.trigger_startup_greeting()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
