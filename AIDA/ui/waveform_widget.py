import random
import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QBrush
from PyQt6.QtCore import Qt, QTimer, QRectF

class WaveformWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(80)
        self.state = "IDLE"
        
        self.num_bars = 30
        self.bar_heights = [5] * self.num_bars
        self.target_heights = [5] * self.num_bars
        
        self.volume = 0.0
        self.time_elapsed = 0
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(30)
        
    def set_state(self, state: str):
        self.state = state
        self.time_elapsed = 0
        
    def update_levels(self, volume: float):
        self.volume = min(1.0, max(0.0, volume))
        
    def update_animation(self):
        self.time_elapsed += 30
        
        if self.state == "IDLE":
            for i in range(self.num_bars):
                if random.random() < 0.1:
                    self.target_heights[i] = random.uniform(2, 10)
        elif self.state == "LISTENING":
            # Map volume to height, with some randomization per bar
            base_h = self.volume * 60
            for i in range(self.num_bars):
                offset = random.uniform(0.5, 1.5)
                h = base_h * offset
                self.target_heights[i] = min(60, max(5, h))
        elif self.state == "PROCESSING":
            for i in range(self.num_bars):
                self.target_heights[i] = 3
        elif self.state == "SPEAKING":
            # Change target every 90ms (approx 3 frames)
            if self.time_elapsed % 90 == 0:
                for i in range(self.num_bars):
                    # Sine wave + noise
                    wave = math.sin(self.time_elapsed / 200.0 + i * 0.5)
                    noise = random.uniform(0, 1)
                    h = 10 + (wave * 0.5 + 0.5) * 30 + noise * 10
                    self.target_heights[i] = min(50, h)
        
        # Smooth interpolation to target
        for i in range(self.num_bars):
            diff = self.target_heights[i] - self.bar_heights[i]
            self.bar_heights[i] += diff * 0.3
            
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fill background #0D0D2B? Wait, the prompt says center panel has #050510 and panels have #0D0D2B.
        # "Background: #0D0D2B" for waveform widget.
        painter.fillRect(self.rect(), QColor("#0D0D2B"))
        
        w = self.width()
        h = self.height()
        
        bar_w = max(2, w / (self.num_bars * 1.5))
        spacing = (w - (self.num_bars * bar_w)) / (self.num_bars + 1)
        
        for i in range(self.num_bars):
            bh = max(2, self.bar_heights[i])
            x = spacing + i * (bar_w + spacing)
            y = (h - bh) / 2
            
            # gradient from #0072FF (bottom) to #00C6FF (top)
            # Actually, the bar is vertically symmetric, so bottom is y+bh, top is y
            grad = QLinearGradient(0, y + bh, 0, y)
            grad.setColorAt(0, QColor("#0072FF"))
            grad.setColorAt(1, QColor("#00C6FF"))
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(QRectF(x, y, bar_w, bh), bar_w/2, bar_w/2)
