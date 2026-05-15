import numpy as np
import sounddevice as sd
from PyQt6.QtCore import QThread, pyqtSignal

class ListenWorker(QThread):
    volume_level = pyqtSignal(float)
    audio_ready = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self._is_recording = False
        self._audio_data = []
        self.sample_rate = 16000

    def run(self):
        self._is_recording = True
        self._audio_data = []
        
        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype='float32') as stream:
                while self._is_recording:
                    data, overflowed = stream.read(int(self.sample_rate * 0.1))
                    if len(data) > 0:
                        self._audio_data.append(data.copy())
                        vol = np.max(np.abs(data))
                        self.volume_level.emit(float(vol))
        except Exception as e:
            print(f"ListenWorker exception: {e}")

        if len(self._audio_data) > 0:
            final_audio = np.concatenate(self._audio_data, axis=0)
            self.audio_ready.emit(final_audio)
        else:
            self.audio_ready.emit(np.array([], dtype='float32'))

    def stop(self):
        self._is_recording = False
