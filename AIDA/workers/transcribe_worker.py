import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from aida_core import transcribe

class TranscribeWorker(QThread):
    text_ready = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, audio_array: np.ndarray):
        super().__init__()
        self.audio_array = audio_array

    def run(self):
        try:
            text = transcribe(self.audio_array)
            self.text_ready.emit(text)
        except Exception as e:
            self.error.emit(str(e))
