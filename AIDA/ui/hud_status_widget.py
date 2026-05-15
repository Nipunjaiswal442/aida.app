from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, QTime
from PyQt6.QtGui import QFont

class HudStatusWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(60)
        self.setStyleSheet("""
            QWidget {
                background-color: #0D0D2B;
                border-bottom: 1px solid #00C6FF;
            }
            QLabel {
                border: none;
            }
        """)
        
        layout = QHBoxLayout()
        self.setLayout(layout)
        
        # Left: AIDA
        self.lbl_aida = QLabel("AIDA")
        font_aida = QFont("Courier", 24, QFont.Weight.Bold)
        self.lbl_aida.setFont(font_aida)
        self.lbl_aida.setStyleSheet("color: #00C6FF;")
        
        # Center: State Label
        self.lbl_state = QLabel("ONLINE")
        font_state = QFont("Courier", 16, QFont.Weight.Bold)
        self.lbl_state.setFont(font_state)
        self.lbl_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Right: Timer
        self.lbl_timer = QLabel("00:00")
        font_timer = QFont("Courier", 16)
        self.lbl_timer.setFont(font_timer)
        self.lbl_timer.setStyleSheet("color: #7B8DB0;")
        self.lbl_timer.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        layout.addWidget(self.lbl_aida)
        layout.addWidget(self.lbl_state)
        layout.addWidget(self.lbl_timer)
        
        self.session_time = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(1000)
        
        self.set_state("IDLE")

    def update_timer(self):
        self.session_time += 1
        m = self.session_time // 60
        s = self.session_time % 60
        self.lbl_timer.setText(f"{m:02d}:{s:02d}")

    def set_state(self, state: str):
        if state == "IDLE":
            self.lbl_state.setText("ONLINE")
            self.lbl_state.setStyleSheet("color: #1A2A6C;")
        elif state == "LISTENING":
            self.lbl_state.setText("LISTENING...")
            self.lbl_state.setStyleSheet("color: #00C6FF;")
        elif state == "PROCESSING":
            self.lbl_state.setText("PROCESSING...")
            self.lbl_state.setStyleSheet("color: #7B2FBE;")
        elif state == "SPEAKING":
            self.lbl_state.setText("SPEAKING...")
            self.lbl_state.setStyleSheet("color: #00FF88;")
