from time import monotonic
import math

import moderngl
import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from ..data.catalog import AU, BODIES
from ..theme import COLORS
from .camera import Camera, pick_body
from .labels import visible_labels
from .overlay import TextOverlay
from .renderer import SceneRenderer
from .scene import body_layout, pick_sphere, trail_history



class Viewport(QOpenGLWidget):
    selected = Signal(object)
    followed = Signal(bool)
    graphics_error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(380, 300)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.camera = Camera()
        self.snapshot = self.previous = None
        self.positions = None
        self.render_elapsed = 0.
        self.selection = 0
        self.follow = False
        self.hover = None
        self.labels = self.trails = self.stars = self.effects = True
        self.physical = False
        self.trail_length = 800
        self.paused = True
        self.last_frame = monotonic()
        self.fps = 0.0
        self.frames = 0
        self.fps_time = monotonic()
        self.ctx = None
        self.error = None
        self.drag_start = self.last_drag = None
        self.dragged = False
        self.renderer = None
        self.sky_brightness = .45
        self.drag_mode = None
        self._visible_labels = set()
        self.text_overlay = TextOverlay(self)
        self.text_overlay.setGeometry(self.rect())
        self.setAccessibleName("Solar system viewport")
        self.setAccessibleDescription("Scroll to zoom; drag to orbit; middle drag or Shift-drag to pan; double click to follow.")

    def initializeGL(self):
        try:
            self.ctx = moderngl.create_context(require=330)
            self.context().aboutToBeDestroyed.connect(self.cleanup)
            self.renderer = SceneRenderer(self.ctx)
        except Exception as exc:
            self.error = f"OpenGL 3.3 initialization failed: {exc}"
            self.graphics_error.emit(self.error)

    def cleanup(self):
        self.makeCurrent()
        if self.renderer:
            self.renderer.release()
            self.renderer = None
        if self.ctx:
            self.ctx.release()
            self.ctx = None
        self.doneCurrent()

    def accept_snapshot(self, snapshot):
        if self.snapshot is not None and snapshot.generation == self.snapshot.generation:
            self.previous = self.snapshot
        else:
            self.previous = None
        self.snapshot = snapshot
        if self.positions is None or self.previous is None:
            self.positions = snapshot.positions.copy()
            self.render_elapsed = snapshot.elapsed

    def set_selection(self, index):
        self.selection = index
        if index is None:
            self.set_follow(False)
        elif self.follow:
            self.set_follow(True)
        self.update()

    def set_follow(self, enabled):
        self.follow = bool(enabled and self.selection is not None)
        radius = BODIES[self.selection].radius if self.follow else 0.
        self.camera.minimum_span = max(.00005*AU, 2.6*radius*math.tan(self.camera.fov/2))
        self.followed.emit(self.follow)

    def focus_body(self, index):
        if self.positions is None:
            return
        self.set_selection(index)
        self.selected.emit(index)
        self.set_follow(True)
        self.camera.preset(self.positions[index], max(BODIES[index].radius*4, .0001*AU))

    def preset(self, name):
        if name in ('Top-down view', '3D view'):
            if name == 'Top-down view':
                self.camera.top_down()
            else:
                self.camera.perspective()
            self.update()
            return
        self.set_follow(False)
        if name == 'Selected' and self.selection is not None:
            self.focus_body(self.selection)
        else:
            span = {'Inner system': 5, 'Outer system': 72, 'Whole system': 78}[name]
            center = self.positions[0] if self.positions is not None else [0, 0, 0]
            self.camera.perspective()
            self.camera.preset(center, span * AU)

    def _interpolate(self, now):
        if self.snapshot is None:
            return
        if self.paused or self.previous is None:
            self.positions = self.snapshot.positions
            self.render_elapsed = self.snapshot.elapsed
            return
        interval = self.snapshot.published - self.previous.published
        alpha = np.clip((now - self.snapshot.published) / max(interval, .016), 0, 1)
        self.positions = self.previous.positions * (1-alpha) + self.snapshot.positions * alpha
        self.render_elapsed = self.previous.elapsed * (1-alpha) + self.snapshot.elapsed * alpha

    def paintGL(self):
        now = monotonic()
        dt = now - self.last_frame
        self.last_frame = now
        self._interpolate(now)
        target = self.positions[self.selection] if (
            self.follow and self.selection is not None and self.positions is not None) else None
        self.camera.animate(dt, target)
        if self.positions is not None:
            self.camera.keep_outside(self.positions, np.array([body.radius for body in BODIES]))
        self.frames += 1
        if now - self.fps_time >= .5:
            self.fps = self.frames / (now - self.fps_time)
            self.frames = 0
            self.fps_time = now
        if self.error or not self.ctx:
            self.text_overlay.update()
            return
        try:
            self._draw_gpu()
        except Exception as exc:
            self.error = f"Rendering failed: {exc}"
            self.graphics_error.emit(self.error)
        self.text_overlay.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.text_overlay.setGeometry(self.rect())
        self.text_overlay.raise_()

    def capture_image(self):
        """Include raster labels when exporting the otherwise GL-only framebuffer."""
        image = self.grabFramebuffer()
        if not image.isNull():
            image.setDevicePixelRatio(self.devicePixelRatioF())
            image.setDotsPerMeterX(round(self.logicalDpiX() / .0254))
            image.setDotsPerMeterY(round(self.logicalDpiY() / .0254))
            painter = QPainter(image)
            try:
                self.text_overlay.paint_content(painter)
            finally:
                painter.end()
        return image

    def _draw_gpu(self):
        w, h = self.width(), self.height()
        dpr = self.devicePixelRatioF()
        fbo = self.ctx.detect_framebuffer(self.defaultFramebufferObject())
        fbo.use()
        self.ctx.viewport = (0, 0, round(w*dpr), round(h*dpr))
        history = None
        if self.trails and self.snapshot is not None and self.positions is not None:
            history = trail_history(self.snapshot, self.render_elapsed, self.positions, self.trail_length)
        self.renderer.draw(self.camera, self.positions, w, h, physical=self.physical,
                           effects=self.effects, stars=self.stars,
                           sky_brightness=self.sky_brightness, history=history)

    def _layout(self):
        return body_layout(self.camera, self.positions, self.width(), self.height(), self.physical)

    def _draw_overlay(self, painter):
        w, h = self.width(), self.height()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(QFont('Sans Serif', 9))
        self._visible_labels = set()
        if self.positions is not None:
            layout = self._layout()
            points, radii = layout.points, layout.screen_radii
            candidates = {}
            order = sorted(range(len(BODIES)), key=lambda i: i != self.selection)
            for i in order:
                p = points[i]
                # Keep the selected marker identifiable when enlarged bodies overlap.
                if (not layout.visible[i] and i != self.selection) or not (0 < p[0] < w and 0 < p[1] < h):
                    continue
                if i in (self.selection, self.hover):
                    painter.setPen(QPen(QColor(COLORS['accent'] if i==self.selection
                                               else COLORS['secondary']),1))
                    radius = max(radii[i], 5)+6
                    painter.drawEllipse(QPointF(*p), radius, radius)
                if not self.labels:
                    continue
                text = BODIES[i].name
                rect = QRectF(p[0]+max(radii[i],5)+11, p[1]-8,
                              painter.fontMetrics().horizontalAdvance(text)+12, 22)
                candidates[i] = (text, rect)
            self._visible_labels = visible_labels(
                {i: (rect.x(), rect.y(), rect.width(), rect.height())
                 for i, (_, rect) in candidates.items()}, self.selection)
            for i in order:
                if i not in self._visible_labels:
                    continue
                text, rect = candidates[i]
                priority = 0 if self.selection is None else self.selection
                painter.setPen(QColor(COLORS['text'] if i==priority else COLORS['secondary']))
                painter.drawText(rect, Qt.AlignmentFlag.AlignVCenter, text)
        painter.setPen(QColor(COLORS['muted']))
        painter.drawText(22, 30, 'SOLAR SYSTEM SIMULATOR')
        if self.snapshot is not None and not self.paused:
            painter.drawText(22, 50, f'Achieved {self.snapshot.achieved_rate / 86400:,.1f} simulated days / second')
        mode = 'Physical radii' if self.physical else 'Enlarged planet radii'
        mode = ('Top-down view' if abs(self.camera.pitch-math.pi/2) < 1e-6 else '3D view') + ' · ' + mode
        painter.drawText(22, h-22, mode)
        # A useful physical scale independent of viewport aspect ratio.
        desired = self.camera.span / h * 110 / AU
        power = 10 ** math.floor(math.log10(max(desired, 1e-12)))
        scale_au = max(x*power for x in (1,2,5,10) if x*power <= desired)
        pixels = scale_au * AU / self.camera.span * h
        painter.drawLine(QPointF(w-25-pixels,h-30), QPointF(w-25,h-30))
        painter.drawText(QRectF(w-185,h-55,160,20), Qt.AlignmentFlag.AlignRight,
                         f'{scale_au:g} AU at focus · {self.fps:.0f} FPS')

    def _pick(self, point):
        if self.positions is None:
            return None
        layout = self._layout()
        hit = pick_sphere(self.camera, self.positions, layout.world_radii, point, self.width(), self.height())
        if hit is not None:
            return hit
        return pick_body(layout.points, layout.screen_radii, point, layout.depths, layout.visible)

    def wheelEvent(self, event):
        pixels = event.pixelDelta().y()
        delta = pixels / 200 if pixels else event.angleDelta().y() / 700
        if not delta:
            event.ignore()
            return
        self.camera.zoom((event.position().x(),event.position().y()),
                         math.exp(-delta),self.width(),self.height(), following=self.follow)
        event.accept()
        self.update()

    def mousePressEvent(self, event):
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.MiddleButton, Qt.MouseButton.RightButton):
            self.drag_start = self.last_drag = event.position()
            self.dragged = False
            self.drag_mode = 'pan' if (event.button() != Qt.MouseButton.LeftButton or
                event.modifiers() & Qt.KeyboardModifier.ShiftModifier) else 'orbit'
            event.accept()

    def mouseMoveEvent(self, event):
        p = event.position()
        if self.drag_start is not None and event.buttons():
            if (p-self.drag_start).manhattanLength() > 4:
                self.dragged = True
            if self.dragged:
                delta = p - self.last_drag
                if self.drag_mode == 'pan':
                    self.set_follow(False)
                    self.camera.pan(delta.x(), delta.y(), self.height())
                else:
                    self.camera.orbit(delta.x(), delta.y())
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.last_drag = p
        else:
            self.hover = self._pick((p.x(), p.y()))
            self.setCursor(Qt.CursorShape.PointingHandCursor if self.hover is not None
                           else Qt.CursorShape.OpenHandCursor)
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.dragged and self.drag_mode == 'orbit':
            self.set_selection(self._pick((event.position().x(), event.position().y())))
            self.selected.emit(self.selection)
        self.drag_start = self.last_drag = self.drag_mode = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.update()

    def mouseDoubleClickEvent(self, event):
        index = self._pick((event.position().x(),event.position().y()))
        if index is not None:
            self.focus_body(index)

    def leaveEvent(self, event):
        self.hover = None
        super().leaveEvent(event)
