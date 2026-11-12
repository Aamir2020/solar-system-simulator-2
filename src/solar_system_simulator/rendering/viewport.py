from importlib.resources import files
from time import monotonic
import math

import moderngl
import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from ..data.catalog import AU, BODIES
from .camera import Camera, display_radii, pick_body


def shader(name):
    return files("solar_system_simulator").joinpath(f"rendering/{name}.glsl").read_text()


def rgb(color):
    return tuple(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))


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
        self.resources = []
        self.setAccessibleName("Solar system viewport")
        self.setAccessibleDescription("Scroll to zoom; drag to pan; click a body to inspect; double click to follow.")

    def initializeGL(self):
        try:
            self.ctx = moderngl.create_context(require=330)
            quad = np.array([[-1,-1], [1,-1], [-1,1], [-1,1], [1,-1], [1,1]], dtype='f4')
            self.quad_buffer = self.ctx.buffer(quad.tobytes())
            self.body_program = self.ctx.program(vertex_shader=shader('quad'),
                                                 fragment_shader=shader('body'))
            self.background_program = self.ctx.program(vertex_shader=shader('quad'),
                                                       fragment_shader=shader('background'))
            self.body_vao = self.ctx.simple_vertex_array(self.body_program, self.quad_buffer, 'in_pos')
            self.background_vao = self.ctx.simple_vertex_array(
                self.background_program, self.quad_buffer, 'in_pos')
            self.trail_program = self.ctx.program(vertex_shader=shader('trail_vertex'),
                                                  fragment_shader=shader('trail_fragment'))
            # Six vertices per segment, four floats per vertex, max 1500 history samples.
            self.trail_buffer = self.ctx.buffer(reserve=1500 * 6 * 4 * 4, dynamic=True)
            self.trail_vao = self.ctx.vertex_array(self.trail_program,
                [(self.trail_buffer, '2f 1f 1f', 'in_pos', 'in_side', 'in_age')])
            self.resources = [self.body_vao, self.background_vao, self.trail_vao,
                              self.quad_buffer, self.trail_buffer, self.body_program,
                              self.background_program, self.trail_program]
            self.context().aboutToBeDestroyed.connect(self.cleanup)
        except Exception as exc:
            self.error = f"OpenGL 3.3 initialization failed: {exc}"
            self.graphics_error.emit(self.error)

    def cleanup(self):
        self.makeCurrent()
        for resource in self.resources:
            resource.release()
        self.resources.clear()
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

    def set_selection(self, index):
        self.selection = index
        if index is None:
            self.set_follow(False)
        self.update()

    def set_follow(self, enabled):
        self.follow = bool(enabled and self.selection is not None)
        self.followed.emit(self.follow)

    def focus_body(self, index):
        if self.positions is None:
            return
        self.set_selection(index)
        self.selected.emit(index)
        # Preserve a useful amount of nearby space while inspecting a planet.
        span = max(BODIES[index].radius * 18, .015 * AU) if index else .2 * AU
        self.camera.preset(self.positions[index], span)
        self.set_follow(True)

    def preset(self, name):
        self.set_follow(False)
        if name == 'Selected' and self.selection is not None:
            self.focus_body(self.selection)
        else:
            span = {'Inner system': 5, 'Outer system': 72, 'Whole system': 78}[name]
            center = self.positions[0] if self.positions is not None else [0, 0]
            self.camera.preset(center, span * AU)

    def _interpolate(self, now):
        if self.snapshot is None:
            return
        if self.paused or self.previous is None:
            self.positions = self.snapshot.positions
            return
        interval = self.snapshot.published - self.previous.published
        alpha = np.clip((now - self.snapshot.published) / max(interval, .016), 0, 1)
        self.positions = self.previous.positions * (1-alpha) + self.snapshot.positions * alpha

    def paintGL(self):
        now = monotonic()
        dt = now - self.last_frame
        self.last_frame = now
        self._interpolate(now)
        target = self.positions[self.selection] if (
            self.follow and self.selection is not None and self.positions is not None) else None
        self.camera.animate(dt, target)
        self.frames += 1
        if now - self.fps_time >= .5:
            self.fps = self.frames / (now - self.fps_time)
            self.frames = 0
            self.fps_time = now
        painter = QPainter(self)
        if self.error or not self.ctx:
            painter.fillRect(self.rect(), QColor('#0b121c'))
            painter.setPen(QColor('#f4c28c'))
            painter.drawText(self.rect().adjusted(40,40,-40,-40),
                Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                self.error or 'Waiting for OpenGL 3.3…')
            painter.end()
            return
        painter.beginNativePainting()
        try:
            self._draw_gpu()
        except Exception as exc:
            self.error = f"Rendering failed: {exc}"
            self.graphics_error.emit(self.error)
        finally:
            painter.endNativePainting()
        self._draw_overlay(painter)
        painter.end()

    def _draw_gpu(self):
        w, h = self.width(), self.height()
        dpr = self.devicePixelRatioF()
        # QOpenGLWidget renders into a Qt-owned framebuffer, not the window's FBO 0.
        fbo = self.ctx.detect_framebuffer(self.defaultFramebufferObject())
        fbo.use()
        self.ctx.viewport = (0, 0, round(w*dpr), round(h*dpr))
        self.ctx.disable(moderngl.DEPTH_TEST | moderngl.CULL_FACE)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        bg = self.background_program
        bg['viewport'].value = (w, h)
        bg['center'].value = (w/2, h/2)
        bg['extent'].value = max(w,h)/2
        bg['stars'].value = self.stars
        self.background_vao.render()
        if self.positions is None:
            return
        points = self.camera.to_screen(self.positions, w, h)
        radii = display_radii(BODIES, self.camera.span, h, self.physical)
        if self.trails and self.snapshot is not None:
            self._draw_trails(w, h)
        program = self.body_program
        program['viewport'].value = (w,h)
        program['effects'].value = self.effects
        for i, (point, radius, body) in enumerate(zip(points, radii, BODIES)):
            extent = radius * 2.25
            if radius < .08 or not (-extent < point[0] < w+extent and -extent < point[1] < h+extent):
                continue
            light = points[0] - point
            length = np.linalg.norm(light)
            if length:
                light = light / length
            else:
                light = np.array([-.6, -.8])
            program['center'].value = tuple(point)
            program['extent'].value = float(extent)
            program['color'].value = rgb(body.color)
            program['kind'].value = i
            program['light_dir'].value = (float(light[0]), -float(light[1]))
            self.body_vao.render()

    def _draw_trails(self, w, h):
        history = self.snapshot.trails[-self.trail_length:]
        if len(history) < 2:
            return
        self.trail_program['viewport'].value = (w, h)
        order = np.array([0,1,2,2,1,3])
        age = np.linspace(.03, 1, len(history))
        for i, body in enumerate(BODIES):
            points = self.camera.to_screen(history[:, i], w, h)
            a, b = points[:-1], points[1:]
            direction = b-a
            lengths = np.linalg.norm(direction, axis=1)
            normal = np.column_stack((-direction[:,1], direction[:,0]))
            normal /= np.maximum(lengths[:,None], 1e-8)
            normal *= 1.6
            corners = np.stack((a-normal,a+normal,b-normal,b+normal),axis=1)
            vertices = np.empty((len(a),6,4),dtype='f4')
            vertices[:,:,:2] = corners[:,order,:]
            vertices[:,:,2] = np.array([-1,1,-1,-1,1,1])
            vertices[:,:,3] = np.stack((age[:-1],age[:-1],age[1:],age[1:],age[:-1],age[1:]),axis=1)
            self.trail_buffer.write(vertices.tobytes())
            self.trail_program['color'].value = rgb(body.color)
            self.trail_vao.render(vertices=len(a)*6)

    def _draw_overlay(self, painter):
        w, h = self.width(), self.height()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(QFont('Sans Serif', 9))
        if self.positions is not None:
            points = self.camera.to_screen(self.positions, w, h)
            radii = display_radii(BODIES, self.camera.span, h, self.physical)
            occupied = []
            order = sorted(range(len(BODIES)), key=lambda i: i != self.selection)
            for i in order:
                p = points[i]
                if not (0 < p[0] < w and 0 < p[1] < h):
                    continue
                if i in (self.selection, self.hover):
                    painter.setPen(QPen(QColor('#efc79b' if i==self.selection else '#849caf'),1))
                    radius = max(radii[i], 5)+6
                    painter.drawEllipse(QPointF(*p), radius, radius)
                if not self.labels:
                    continue
                text = BODIES[i].name + ('  / FOLLOWING' if self.follow and i==self.selection else '')
                rect = QRectF(p[0]+max(radii[i],5)+11, p[1]-8,
                              painter.fontMetrics().horizontalAdvance(text)+12, 22)
                if i != self.selection and any(rect.intersects(other) for other in occupied):
                    continue
                occupied.append(rect)
                painter.setPen(QColor('#f0d0aa' if i==self.selection else '#adbace'))
                painter.drawText(rect, Qt.AlignmentFlag.AlignVCenter, text)
        painter.setPen(QColor('#7d8da4'))
        painter.drawText(22, 30, 'ORBITAL / LIVE SIMULATION')
        if self.snapshot is not None and not self.paused:
            painter.drawText(22, 50, f'Achieved {self.snapshot.achieved_rate / 86400:,.1f} simulated days / second')
        mode = 'Physical radii' if self.physical else 'Exaggerated radii · distances to scale'
        painter.drawText(22, h-22, mode)
        # A useful physical scale independent of viewport aspect ratio.
        desired = self.camera.span / h * 110 / AU
        power = 10 ** math.floor(math.log10(max(desired, 1e-12)))
        scale_au = max(x*power for x in (1,2,5,10) if x*power <= desired)
        pixels = scale_au * AU / self.camera.span * h
        painter.drawLine(QPointF(w-25-pixels,h-30), QPointF(w-25,h-30))
        painter.drawText(QRectF(w-185,h-55,160,20), Qt.AlignmentFlag.AlignRight,
                         f'{scale_au:g} AU  ·  {self.fps:.0f} FPS')

    def _pick(self, point):
        if self.positions is None:
            return None
        points = self.camera.to_screen(self.positions, self.width(), self.height())
        radii = display_radii(BODIES, self.camera.span, self.height(), self.physical)
        return pick_body(points, radii, point)

    def wheelEvent(self, event):
        self.camera.zoom((event.position().x(),event.position().y()),
                         math.exp(-event.angleDelta().y()/700),self.width(),self.height())
        # Follow stays anchored to the selected body after the cursor-centered zoom.
        event.accept()
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start = self.last_drag = event.position()
            self.dragged = False

    def mouseMoveEvent(self, event):
        p = event.position()
        if self.drag_start is not None and event.buttons() & Qt.MouseButton.LeftButton:
            if (p-self.drag_start).manhattanLength() > 4:
                self.dragged = True
            if self.dragged:
                self.set_follow(False)
                delta = p - self.last_drag
                self.camera.pan(delta.x(),delta.y(),self.height())
            self.last_drag = p
        else:
            self.hover = self._pick((p.x(),p.y()))
            self.setCursor(Qt.CursorShape.PointingHandCursor if self.hover is not None
                           else Qt.CursorShape.OpenHandCursor)
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.dragged:
            self.set_selection(self._pick((event.position().x(),event.position().y())))
            self.selected.emit(self.selection)
        self.drag_start = self.last_drag = None

    def mouseDoubleClickEvent(self, event):
        index = self._pick((event.position().x(),event.position().y()))
        if index is not None:
            self.focus_body(index)

    def leaveEvent(self, event):
        self.hover = None
        super().leaveEvent(event)
