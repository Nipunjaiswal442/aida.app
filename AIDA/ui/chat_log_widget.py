from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QLabel, QHBoxLayout, QScrollBar
from PyQt6.QtCore import Qt, QTimer
from datetime import datetime
import html

class ChatLogWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(200)
        self.setStyleSheet("background-color: #0D0D2B;")
        
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea { border: none; }
            QScrollBar:vertical {
                border: none;
                background: #050510;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #1A2A6C;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)
        
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background-color: transparent;")
        self.content_layout = QVBoxLayout()
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.content_widget.setLayout(self.content_layout)
        
        self.scroll_area.setWidget(self.content_widget)
        self.layout.addWidget(self.scroll_area)
        
        self.messages = []
        
    def add_message(self, sender: str, text: str):
        if len(self.messages) >= 50:
            old_msg = self.messages.pop(0)
            self.content_layout.removeWidget(old_msg)
            old_msg.deleteLater()
            
        msg_widget = QWidget()
        msg_widget.setStyleSheet("background-color: transparent;")
        msg_layout = QHBoxLayout()
        msg_layout.setContentsMargins(10, 5, 10, 5)
        msg_widget.setLayout(msg_layout)
        
        time_str = datetime.now().strftime("%H:%M")
        safe_text = html.escape(text).replace("\n", "<br>")
        
        lbl_msg = QLabel()
        lbl_msg.setWordWrap(True)
        lbl_msg.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        if sender == "AIDA":
            lbl_msg.setText(f"<span style='color: #7B8DB0; font-size: 10px;'>{time_str}</span>&nbsp;&nbsp;<b>AIDA:</b> {safe_text}")
            lbl_msg.setStyleSheet("background-color: #0A1545; color: #00C6FF; border-radius: 8px; padding: 8px;")
            msg_layout.addWidget(lbl_msg)
            msg_layout.addStretch()
        else:
            lbl_msg.setText(f"{safe_text} <b>:You</b>&nbsp;&nbsp;<span style='color: #7B8DB0; font-size: 10px;'>{time_str}</span>")
            lbl_msg.setStyleSheet("background-color: #1A2A6C; color: #E0E8FF; border-radius: 8px; padding: 8px;")
            msg_layout.addStretch()
            msg_layout.addWidget(lbl_msg)
            
        self.content_layout.addWidget(msg_widget)
        self.messages.append(msg_widget)
        
        # Scroll to bottom slightly after layout updates
        QTimer.singleShot(50, self.scroll_to_bottom)
        
    def scroll_to_bottom(self):
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
