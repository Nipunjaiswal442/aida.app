from PyQt6.QtCore import QThread, pyqtSignal

class TimerAlertWorker(QThread):
    alert_triggered = pyqtSignal(str)

    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def run(self):
        self.alert_triggered.emit(self.message)
