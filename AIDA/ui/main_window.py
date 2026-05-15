from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QApplication, QLineEdit
import mac_tools
from workers.tools_worker import TimerAlertWorker
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent

from ui.hud_status_widget import HudStatusWidget
from ui.orb_widget import OrbWidget
from ui.waveform_widget import WaveformWidget
from ui.chat_log_widget import ChatLogWidget

from workers.listen_worker import ListenWorker
from workers.transcribe_worker import TranscribeWorker
from workers.llm_worker import LLMWorker
from workers.speak_worker import SpeakWorker
from workers.wakeword_worker import WakeWordWorker

class TalkButton(QPushButton):
    pressed_signal = pyqtSignal()
    released_signal = pyqtSignal()

    def __init__(self, text):
        super().__init__(text)
        
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.pressed_signal.emit()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.released_signal.emit()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AIDA - Desktop Voice Assistant")
        self.setFixedSize(900, 700)
        self.setStyleSheet("background-color: #050510;")
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.central_widget.setLayout(self.main_layout)
        
        # ZONE 1
        self.hud = HudStatusWidget()
        self.main_layout.addWidget(self.hud)
        
        # ZONE 2
        zone2 = QWidget()
        zone2.setStyleSheet("background-color: #050510;")
        zone2_layout = QVBoxLayout()
        zone2.setLayout(zone2_layout)
        
        self.orb = OrbWidget()
        zone2_layout.addWidget(self.orb, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.waveform = WaveformWidget()
        zone2_layout.addWidget(self.waveform)
        
        controls_layout = QHBoxLayout()
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_talk = TalkButton("🎤  HOLD TO TALK")
        self.btn_talk.setFixedSize(250, 50)
        self.btn_talk.setStyleSheet("""
            QPushButton {
                background-color: #0D0D2B;
                color: #E0E8FF;
                border: 2px solid #0072FF;
                border-radius: 25px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:pressed {
                background-color: #0072FF;
            }
        """)
        
        self.btn_gear = QPushButton("⚙")
        self.btn_gear.setFixedSize(50, 50)
        self.btn_gear.setToolTip("Settings (v2.0 Scope)")
        self.btn_gear.setStyleSheet("""
            QPushButton {
                background-color: #0D0D2B;
                color: #7B8DB0;
                border: 2px solid #1A2A6C;
                border-radius: 25px;
                font-size: 20px;
            }
        """)
        
        controls_layout.addWidget(self.btn_talk)
        controls_layout.addWidget(self.btn_gear)
        zone2_layout.addLayout(controls_layout)
        
        # Text Input Row
        self.text_input_layout = QHBoxLayout()
        self.text_input_layout.setContentsMargins(50, 10, 50, 10)
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Type a message...")
        self.text_input.setStyleSheet("""
            QLineEdit {
                background-color: #0D0D2B;
                border: 1px solid #0072FF;
                border-radius: 8px;
                color: #E0E8FF;
                font-family: sans-serif;
                font-size: 14px;
                padding: 8px;
            }
            QLineEdit:focus {
                border: 1px solid #00C6FF;
            }
        """)
        
        self.btn_send = QPushButton("SEND →")
        self.btn_send.setFixedSize(80, 36)
        self.btn_send.setStyleSheet("""
            QPushButton {
                background-color: #0D0D2B;
                color: #E0E8FF;
                border: 2px solid #0072FF;
                border-radius: 18px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:pressed {
                background-color: #0072FF;
            }
            QPushButton:disabled {
                border: 2px solid #333355;
                color: #777799;
            }
        """)
        
        self.text_input_layout.addWidget(self.text_input)
        self.text_input_layout.addWidget(self.btn_send)
        zone2_layout.addLayout(self.text_input_layout)
        
        self.main_layout.addWidget(zone2)
        
        # ZONE 3
        self.chat_log = ChatLogWidget()
        self.main_layout.addWidget(self.chat_log)
        
        # Connect button
        self.btn_talk.pressed_signal.connect(self.start_listening)
        self.btn_talk.released_signal.connect(self.stop_listening)
        self.btn_send.clicked.connect(self.send_text_message)
        self.text_input.returnPressed.connect(self.send_text_message)
        
        # State
        self.current_state = "IDLE"
        
        # Workers
        self.listen_worker = None
        self.transcribe_worker = None
        self.llm_worker = None
        self.speak_worker = None
        self.timer_alert_worker = None
        self.wakeword_worker = None

        mac_tools.register_timer_callback(self.on_timer_alert)

        # Start wake word listener
        self._start_wakeword_listener()


    def _start_wakeword_listener(self):
        """Start the background wake word detection thread."""
        self.wakeword_worker = WakeWordWorker()
        self.wakeword_worker.wake_word_detected.connect(self.on_wake_word_detected)
        self.wakeword_worker.error.connect(self.on_worker_error)
        self.wakeword_worker.status_update.connect(self._on_wakeword_status)
        self.wakeword_worker.start()

    def _on_wakeword_status(self, status):
        """Handle wake word status updates."""
        print(status)

    def on_wake_word_detected(self):
        """Called when the wake word 'Hey AIDA' is detected."""
        if self.current_state != "IDLE":
            # Already busy, ignore wake word
            if self.wakeword_worker:
                self.wakeword_worker.resume()
            return

        # Speak acknowledgment, then start listening
        self.set_state("SPEAKING")
        self.speak_worker = SpeakWorker("Yes?")
        self.speak_worker.speak_done.connect(self._on_wake_ack_done)
        self.speak_worker.error.connect(self.on_worker_error)
        self.speak_worker.start()

    def _on_wake_ack_done(self):
        """After saying 'Yes?', automatically start listening for the command."""
        self.set_state("LISTENING")
        self.listen_worker = ListenWorker()
        self.listen_worker.volume_level.connect(self.waveform.update_levels)
        self.listen_worker.audio_ready.connect(self.on_audio_ready)
        self.listen_worker.start()
        # Auto-stop listening after 8 seconds for wake word mode
        from PyQt6.QtCore import QTimer
        self._wake_listen_timer = QTimer()
        self._wake_listen_timer.setSingleShot(True)
        self._wake_listen_timer.timeout.connect(self._stop_wake_listening)
        self._wake_listen_timer.start(8000)

    def _stop_wake_listening(self):
        """Auto-stop listening after timeout in wake word mode."""
        if self.current_state == "LISTENING" and self.listen_worker:
            self.listen_worker.stop()

    def trigger_startup_greeting(self):
        self.set_state("SPEAKING")
        self.speak_worker = SpeakWorker("Hello! I am AIDA, your personal assistant. I am ready when you are.")
        self.speak_worker.speak_done.connect(self.on_speak_done)
        self.speak_worker.error.connect(self.on_worker_error)
        self.speak_worker.start()

    def set_state(self, state: str):
        self.current_state = state
        self.hud.set_state(state)
        self.orb.set_state(state)
        self.waveform.set_state(state)
        
        # Disable text input during PROCESSING or SPEAKING
        if state in ["PROCESSING", "SPEAKING"]:
            self.text_input.setEnabled(False)
            self.btn_send.setEnabled(False)
            # Pause wake word during active interaction
            if self.wakeword_worker:
                self.wakeword_worker.pause()
        else:
            self.text_input.setEnabled(True)
            self.btn_send.setEnabled(True)
            # Resume wake word when idle
            if self.wakeword_worker:
                self.wakeword_worker.resume()

    def start_listening(self):
        if self.current_state != "IDLE":
            return
        self.set_state("LISTENING")
        # Pause wake word during manual listening
        if self.wakeword_worker:
            self.wakeword_worker.pause()
        self.listen_worker = ListenWorker()
        self.listen_worker.volume_level.connect(self.waveform.update_levels)
        self.listen_worker.audio_ready.connect(self.on_audio_ready)
        self.listen_worker.start()

    def stop_listening(self):
        if self.current_state == "LISTENING" and self.listen_worker:
            self.listen_worker.stop()

    def on_audio_ready(self, audio_array):
        if audio_array.size == 0:
            self.set_state("IDLE")
            return
            
        self.set_state("PROCESSING")
        self.transcribe_worker = TranscribeWorker(audio_array)
        self.transcribe_worker.text_ready.connect(self.on_text_ready)
        self.transcribe_worker.error.connect(self.on_worker_error)
        self.transcribe_worker.start()

    def send_text_message(self):
        if self.current_state != "IDLE":
            return
            
        text = self.text_input.text().strip()
        if not text:
            return
            
        self.text_input.clear()
        self.chat_log.add_message("User", text)
        self.set_state("PROCESSING")
        
        self.llm_worker = LLMWorker(text)
        self.llm_worker.reply_ready.connect(self.on_reply_ready)
        self.llm_worker.error.connect(self.on_worker_error)
        self.llm_worker.start()

    def on_text_ready(self, text):
        if not text:
            self.chat_log.add_message("AIDA", "I didn't catch that. Please try again.")
            self.set_state("IDLE")
            return
            
        self.chat_log.add_message("User", text)
        self.llm_worker = LLMWorker(text)
        self.llm_worker.reply_ready.connect(self.on_reply_ready)
        self.llm_worker.error.connect(self.on_worker_error)
        self.llm_worker.start()

    def on_reply_ready(self, reply):
        self.chat_log.add_message("AIDA", reply)
        self.set_state("SPEAKING")
        self.speak_worker = SpeakWorker(reply)
        self.speak_worker.speak_done.connect(self.on_speak_done)
        self.speak_worker.error.connect(self.on_worker_error)
        self.speak_worker.start()

    def on_speak_done(self):
        self.set_state("IDLE")

    def on_timer_alert(self, message):
        self.timer_alert_worker = TimerAlertWorker(message)
        self.timer_alert_worker.alert_triggered.connect(self.handle_timer_alert)
        self.timer_alert_worker.start()

    def handle_timer_alert(self, message):
        self.chat_log.add_message("AIDA", message)
        self.set_state("SPEAKING")
        self.speak_worker = SpeakWorker(message)
        self.speak_worker.speak_done.connect(self.on_speak_done)
        self.speak_worker.error.connect(self.on_worker_error)
        self.speak_worker.start()

    def on_worker_error(self, error_str):
        self.chat_log.add_message("AIDA", f"[Error] {error_str}")
        self.set_state("IDLE")

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self.start_listening()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self.stop_listening()
        else:
            super().keyReleaseEvent(event)

    def closeEvent(self, event):
        if getattr(self, "_is_closing", False):
            event.accept()
            return
            
        event.ignore()
        self._is_closing = True

        # Stop wake word listener
        if self.wakeword_worker:
            self.wakeword_worker.stop()

        self.set_state("SPEAKING")
        self.speak_worker = SpeakWorker("Goodbye! AIDA going offline.")
        self.speak_worker.speak_done.connect(self.final_close)
        self.speak_worker.error.connect(self.final_close)
        self.speak_worker.start()
        
    def final_close(self):
        if self.listen_worker:
            self.listen_worker.stop()
        if self.wakeword_worker:
            self.wakeword_worker.stop()
        self.close()
