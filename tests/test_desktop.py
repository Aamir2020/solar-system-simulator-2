"""Opt-in real Qt/ModernGL integration smoke check (run under a desktop or Xvfb)."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic, sleep
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.environ.get('ORBITAL_DESKTOP_TESTS') == '1',
                     'Set ORBITAL_DESKTOP_TESTS=1 on a host with Qt, ModernGL and a display')
class DesktopTests(unittest.TestCase):
    def test_window_render_resize_selection_and_single_step(self):
        from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, QSettings, Qt
        from PySide6.QtGui import QColor, QFont, QMouseEvent, QPaintEngine, QPainter, QSurfaceFormat, QWheelEvent
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication
        from solar_system_simulator.ui.window import MainWindow
        from solar_system_simulator.theme import COLORS
        from support import sample_scenario
        from solar_system_simulator.data.horizons import HorizonsError
        def wait_until(predicate):
            deadline = monotonic() + 5
            while not predicate() and monotonic() < deadline:
                QTest.qWait(10)
                sleep(.005)  # Let the physics worker run even on slow software renderers.
            self.assertTrue(predicate(), 'Desktop state did not update before the timeout')
        with TemporaryDirectory() as directory:
            QSettings.setDefaultFormat(QSettings.Format.IniFormat)
            QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,directory)
            fmt=QSurfaceFormat()
            fmt.setVersion(3,3)
            fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
            fmt.setSamples(4)
            QSurfaceFormat.setDefaultFormat(fmt)
            app=QApplication.instance() or QApplication([])
            window=MainWindow()
            try:
                window.show()
                QTest.qWait(500)
                self.assertIsNone(window.view.error)
                self.assertIsNotNone(window.view.ctx)
                self.assertIsNone(window.scenario)
                self.assertIsNone(window.view.snapshot)
                self.assertFalse(window.play_button.isEnabled())
                window._toggle_play()
                window._step()
                window._restart()
                self.assertTrue(window.view.paused)
                self.assertIsNone(window.runner.latest())
                # Failed initial loading must not enable playback or supply fake state.
                with patch('solar_system_simulator.ui.window.HorizonsClient.load',
                           side_effect=HorizonsError('Test connection failure')), \
                     patch('solar_system_simulator.ui.window.QMessageBox.warning') as warning:
                    window.load_button.click()
                    wait_until(lambda: warning.called)
                self.assertIsNone(window.scenario)
                self.assertIsNone(window.runner.state)
                self.assertFalse(window.play_button.isEnabled())
                # The real loader path receives a fixture only inside this network-free test.
                scenario = sample_scenario()
                with patch('solar_system_simulator.ui.window.HorizonsClient.load', return_value=scenario):
                    window.load_button.click()
                    wait_until(lambda: window.scenario is scenario)
                wait_until(lambda: window.view.snapshot is not None)
                self.assertTrue(window.play_button.isEnabled())
                with patch('solar_system_simulator.ui.window.HorizonsClient.load',
                           side_effect=HorizonsError('Test reload failure')), \
                     patch('solar_system_simulator.ui.window.QMessageBox.warning') as warning:
                    window.load_button.click()
                    wait_until(lambda: warning.called)
                self.assertIs(window.scenario, scenario)
                self.assertTrue(window.play_button.isEnabled())
                self.assertIsNotNone(window.view.snapshot)
                self.assertTrue(window.view.frames > 0 or window.view.fps > 0)
                window.resize(1200,760)
                QTest.qWait(100)
                image=window.view.grabFramebuffer()
                self.assertFalse(image.isNull())
                output=Path(directory)/'viewport.png'
                self.assertTrue(image.save(str(output)))
                self.assertGreater(output.stat().st_size,1000)
                self.assertEqual(window.view.text_overlay.paint_engine_type, QPaintEngine.Type.Raster)
                self.assertEqual(window.view.text_overlay.geometry(), window.view.rect())
                self.assertTrue(window.view.text_overlay.testAttribute(
                    Qt.WidgetAttribute.WA_TransparentForMouseEvents))
                # Compare exported header glyphs with independent raster text on the GL scene.
                scene = window.view.grabFramebuffer()
                composed = window.view.capture_image()
                reference = scene.copy()
                reference.setDevicePixelRatio(composed.devicePixelRatio())
                reference.setDotsPerMeterX(composed.dotsPerMeterX())
                reference.setDotsPerMeterY(composed.dotsPerMeterY())
                painter = QPainter(reference)
                painter.setFont(QFont('Sans Serif', 9))
                painter.setPen(QColor(COLORS['muted']))
                painter.drawText(22, 30, 'ORBITAL / LIVE SIMULATION')
                painter.end()
                ratio = composed.devicePixelRatio()
                header = QRect(round(20*ratio), round(14*ratio), round(280*ratio), round(20*ratio))
                self.assertEqual(composed.copy(header), reference.copy(header))
                self.assertNotEqual(composed.copy(header), scene.copy(header))
                # Exercise the hover callback that exposed the native None refcount crash.
                for i in range(1000):
                    point = QPointF(30 + i % 200, 50 + i % 150)
                    event = QMouseEvent(
                        QEvent.Type.MouseMove, point, point,
                        Qt.MouseButton.NoButton, Qt.MouseButton.NoButton,
                        Qt.KeyboardModifier.NoModifier,
                    )
                    app.sendEvent(window.view, event)
                QTest.qWait(50)
                self.assertIsNone(window.view.error)
                # At system scale, crowded inner names hide together, except the priority.
                from solar_system_simulator.data.catalog import AU
                window.view.camera.span = window.view.camera.target_span = 2000*AU
                window.view.set_selection(None)
                wait_until(lambda: window.view._visible_labels == {0})
                self.assertEqual(window.view._visible_labels, {0})
                window.body_list.setCurrentRow(3)
                self.assertEqual(window.view.selection,3)
                wait_until(lambda: window.view._visible_labels == {3})
                self.assertEqual(window.view._visible_labels, {3})
                window._focus_selection()
                self.assertTrue(window.view.follow)
                self.assertEqual(window.view.snapshot.elapsed,0)
                window._step()
                wait_until(lambda: window.view.snapshot.elapsed == 86400)
                self.assertEqual(window.view.snapshot.elapsed,86400)
                window._restart()
                wait_until(lambda: window.view.snapshot.elapsed == 0)
                self.assertEqual(window.view.snapshot.elapsed,0)
                self.assertIsNone(window.view.error)
                # Play follows the selected planet without requiring the Follow button.
                window.view.set_follow(False)
                window.play_button.click()
                self.assertTrue(window.view.follow)
                self.assertTrue(window.follow_button.isChecked())
                wait_until(lambda: window.view.snapshot.elapsed > 0)
                self.assertGreater(window.view.snapshot.elapsed, 0)
                # Wheel and trackpad zoom must keep a moving, followed body centered.
                import numpy as np
                for pixels, angle in ((0, 120), (0, -120), (12, 0), (-12, 0)):
                    camera = window.view.camera
                    before_span = camera.span
                    before_center = camera.center.copy()
                    point = QPointF(80, 120)  # Deliberately away from the body.
                    wheel = QWheelEvent(
                        point, point, QPoint(0, pixels), QPoint(0, angle),
                        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                        Qt.ScrollPhase.ScrollUpdate, False,
                    )
                    app.sendEvent(window.view, wheel)
                    self.assertEqual(camera.span, before_span)
                    np.testing.assert_array_equal(camera.center, before_center)
                    wait_until(lambda: camera.span != before_span)
                    screen = camera.to_screen(window.view.positions[3],
                                              window.view.width(), window.view.height())
                    np.testing.assert_allclose(screen,
                        [window.view.width()/2, window.view.height()/2], atol=1e-8)
                window.view.set_follow(False)
                window.body_list.setCurrentRow(4)
                self.assertEqual(window.view.selection, 4)
                self.assertTrue(window.view.follow)
                QTest.qWait(50)
                import numpy as np
                np.testing.assert_array_equal(window.view.camera.target_center, window.view.positions[4])
                # Viewport clicks also retarget following, and empty-space clicks release it.
                window.view.set_follow(False)
                window.view.set_selection(2)
                window._select_from_view(2)
                self.assertTrue(window.view.follow)
                window.view.set_selection(None)
                window._select_from_view(None)
                self.assertFalse(window.view.follow)
                window.play_button.click()
            finally:
                window.close()
                app.processEvents()
            self.assertFalse(window.runner.thread.is_alive())
