import asyncio
from PyQt6.QtCore import QThread, pyqtSignal
from aida_core import speak

class SpeakWorker(QThread):
    speak_done = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, text: str):
        super().__init__()
        self.text = text

    def run(self):
        try:
            asyncio.run(speak(self.text))
            self.speak_done.emit()
        except Exception as e:
            self.error.emit(str(e))
