from PyQt6.QtCore import QThread, pyqtSignal
from aida_core import ask_aida

class LLMWorker(QThread):
    reply_ready = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, text: str):
        super().__init__()
        self.text = text

    def run(self):
        try:
            reply = ask_aida(self.text)
            self.reply_ready.emit(reply)
        except Exception as e:
            self.error.emit(str(e))
