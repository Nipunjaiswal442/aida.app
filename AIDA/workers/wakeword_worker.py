import numpy as np
import pyaudio
from PyQt6.QtCore import QThread, pyqtSignal

try:
    from openwakeword.model import Model as WakeModel
    WAKEWORD_AVAILABLE = True
except ImportError:
    WAKEWORD_AVAILABLE = False


class WakeWordWorker(QThread):
    """Background thread that listens for the 'Hey AIDA' wake word.
    
    Uses the hey_jarvis openWakeWord model as a stand-in for 'Hey AIDA'.
    Emits wake_word_detected when the wake word is heard.
    """
    wake_word_detected = pyqtSignal()
    error = pyqtSignal(str)
    status_update = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._running = False
        self._paused = False

    def run(self):
        if not WAKEWORD_AVAILABLE:
            self.error.emit("openWakeWord not installed. Wake word disabled.")
            return

        self._running = True
        pa = None
        stream = None

        try:
            oww_model = WakeModel(wakeword_models=["hey_jarvis"], inference_framework="onnx")
            pa = pyaudio.PyAudio()
            stream = pa.open(
                rate=16000,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=1280
            )
            self.status_update.emit("👂 Wake word listener active")

            while self._running:
                if self._paused:
                    # While paused (during active interaction), just drain audio
                    try:
                        stream.read(1280, exception_on_overflow=False)
                    except Exception:
                        pass
                    self.msleep(50)
                    continue

                try:
                    audio_chunk = np.frombuffer(
                        stream.read(1280, exception_on_overflow=False),
                        dtype=np.int16
                    )
                    oww_model.predict(audio_chunk)
                    scores = list(oww_model.prediction_buffer.values())
                    if scores and max(scores[-1]) > 0.5:
                        print("✅ Wake word detected!")
                        self.status_update.emit("✅ Wake word detected!")
                        # Reset predictions to avoid double-trigger
                        oww_model.reset()
                        self.wake_word_detected.emit()
                        # Pause briefly to avoid immediate re-detection
                        self._paused = True
                except Exception:
                    pass

        except Exception as e:
            self.error.emit(f"Wake word error: {e}")
        finally:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            if pa:
                try:
                    pa.terminate()
                except Exception:
                    pass

    def pause(self):
        """Pause wake word detection (during active interaction)."""
        self._paused = True

    def resume(self):
        """Resume wake word detection."""
        self._paused = False
        self.status_update.emit("👂 Wake word listener active")

    def stop(self):
        """Stop the worker entirely."""
        self._running = False
        self.wait(3000)
