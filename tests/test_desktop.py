"""Opt-in real Qt/ModernGL integration smoke check (run under a desktop or Xvfb)."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


@unittest.skipUnless(os.environ.get('ORBITAL_DESKTOP_TESTS') == '1',
                     'Set ORBITAL_DESKTOP_TESTS=1 on a host with Qt, ModernGL and a display')
class DesktopTests(unittest.TestCase):
    def test_window_render_resize_selection_and_single_step(self):
        from PySide6.QtCore import QEvent, QPointF, QSettings, Qt
        from PySide6.QtGui import QMouseEvent, QSurfaceFormat
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication
        from solar_system_simulator.ui.window import MainWindow
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
                self.assertIsNotNone(window.view.snapshot)
                self.assertTrue(window.view.frames > 0 or window.view.fps > 0)
                window.resize(1200,760)
                QTest.qWait(100)
                image=window.view.grabFramebuffer()
                self.assertFalse(image.isNull())
                output=Path(directory)/'viewport.png'
                self.assertTrue(image.save(str(output)))
                self.assertGreater(output.stat().st_size,1000)
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
                QTest.qWait(50)
                self.assertEqual(window.view._visible_labels, {0})
                window.body_list.setCurrentRow(3)
                self.assertEqual(window.view.selection,3)
                QTest.qWait(50)
                self.assertEqual(window.view._visible_labels, {3})
                window._focus_selection()
                self.assertTrue(window.view.follow)
                self.assertEqual(window.view.snapshot.elapsed,0)
                window._step()
                QTest.qWait(150)
                self.assertEqual(window.view.snapshot.elapsed,86400)
                window._restart()
                QTest.qWait(100)
                self.assertEqual(window.view.snapshot.elapsed,0)
                self.assertIsNone(window.view.error)
            finally:
                window.close()
                app.processEvents()
            self.assertFalse(window.runner.thread.is_alive())
