"""Raster text above the OpenGL scene, independent of its texture bindings."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget


class TextOverlay(QWidget):
    def __init__(self, viewport):
        super().__init__(viewport)
        self.viewport = viewport
        self.paint_engine_type = None
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAutoFillBackground(False)
        self.setStyleSheet('background: transparent;')
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def paint_content(self, painter):
        viewport = self.viewport
        if viewport.error or viewport.ctx is None:
            painter.fillRect(viewport.rect(), QColor('#0b121c'))
            painter.setPen(QColor('#f4c28c'))
            painter.drawText(
                viewport.rect().adjusted(40, 40, -40, -40),
                Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                viewport.error or 'Waiting for OpenGL 3.3…',
            )
        else:
            viewport._draw_overlay(painter)

    def paintEvent(self, event):
        painter = QPainter(self)
        self.paint_engine_type = painter.paintEngine().type()
        try:
            self.paint_content(painter)
        finally:
            painter.end()
