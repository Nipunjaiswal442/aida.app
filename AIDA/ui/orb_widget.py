import math
import random
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QPen, QBrush
from PyQt6.QtCore import Qt, QTimer, QRectF

class OrbWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(300, 300)
        self.state = "IDLE"
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(30)
        
        self.time_elapsed = 0
        self.arc_angle = 0
        
        self.glow_radius_base = 120
        self.glow_radius = self.glow_radius_base
        
        self.ring_radius = 120
        
    def set_state(self, state: str):
        self.state = state
        self.time_elapsed = 0
        self.ring_radius = 120
        
    def update_animation(self):
        self.time_elapsed += 30
        
        if self.state == "IDLE":
            # ±10px on a 2-second sine wave
            self.glow_radius = self.glow_radius_base + 10 * math.sin(2 * math.pi * (self.time_elapsed / 2000))
        elif self.state == "LISTENING":
            # ±20px rapidly (0.5s cycle)
            self.glow_radius = self.glow_radius_base + 20 * math.sin(2 * math.pi * (self.time_elapsed / 500))
            # expanding ring
            self.ring_radius += 2
            if self.ring_radius > 200:
                self.ring_radius = 120
        elif self.state == "PROCESSING":
            # rotating arc
            self.arc_angle = (self.arc_angle - 8) % 360
            self.glow_radius = self.glow_radius_base + 5 * math.sin(2 * math.pi * (self.time_elapsed / 1500))
        elif self.state == "SPEAKING":
            # ±15px in a 0.3s cycle (sine wave with random variation)
            variation = random.uniform(-3, 3)
            self.glow_radius = self.glow_radius_base + 15 * math.sin(2 * math.pi * (self.time_elapsed / 300)) + variation
            
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center_x = self.width() / 2
        center_y = self.height() / 2
        
        core_color = QColor("#1A2A6C")
        edge_color = QColor("#0A1545")
        
        if self.state == "IDLE":
            core_color = QColor("#1A2A6C")
            edge_color = QColor("#0A1545")
        elif self.state == "LISTENING":
            core_color = QColor("#00C6FF")
            edge_color = QColor("#003399")
        elif self.state == "PROCESSING":
            core_color = QColor("#7B2FBE")
            edge_color = QColor("#3D0073")
        elif self.state == "SPEAKING":
            core_color = QColor("#00FF88")
            edge_color = QColor("#006633")
            
        # Draw background or let main window handle it, we'll assume transparent widget bg
        # Draw concentric glow rings
        if self.state == "LISTENING":
            opacity = max(0, 255 - int(255 * ((self.ring_radius - 120) / 80)))
            ring_pen = QPen(core_color)
            ring_pen.setWidth(2)
            ring_color = QColor(core_color)
            ring_color.setAlpha(opacity)
            painter.setPen(QPen(ring_color, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QRectF(center_x - self.ring_radius, center_y - self.ring_radius, 
                                       self.ring_radius * 2, self.ring_radius * 2))
        elif self.state == "IDLE":
            painter.setPen(QPen(QColor(10, 21, 69, 50), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QRectF(center_x - 140, center_y - 140, 280, 280))

        # Main sphere
        gradient = QRadialGradient(center_x, center_y, self.glow_radius)
        gradient.setColorAt(0, core_color)
        gradient.setColorAt(1, edge_color)
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(QRectF(center_x - self.glow_radius, center_y - self.glow_radius, 
                                   self.glow_radius * 2, self.glow_radius * 2))
                                   
        # Draw rotating arc for PROCESSING
        if self.state == "PROCESSING":
            pen = QPen(QColor("#00C6FF"))
            pen.setWidth(4)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            rect = QRectF(center_x - self.glow_radius - 10, center_y - self.glow_radius - 10, 
                          (self.glow_radius + 10) * 2, (self.glow_radius + 10) * 2)
            # drawArc takes angles in 1/16th of a degree
            painter.drawArc(rect, int(self.arc_angle * 16), 120 * 16)
