import importlib.util
import os
import subprocess
import sys
import textwrap
import unittest
from unittest.mock import patch

from solar_system_simulator.app import main
from solar_system_simulator.runtime import desktop_compatibility_error


class RuntimeTests(unittest.TestCase):
    def test_headless_requires_explicit_nasa_epoch(self):
        with patch('sys.stderr'), self.assertRaises(SystemExit) as exit:
            main(['--headless'])
        self.assertEqual(exit.exception.code, 2)

    def test_headless_uses_nasa_client_instead_of_bundled_state(self):
        from support import sample_scenario
        scenario = sample_scenario()
        with patch('solar_system_simulator.data.horizons.HorizonsClient.load', return_value=scenario) as load, \
             patch('sys.stdout') as stdout:
            self.assertEqual(main(['--headless', '--epoch', '2026-01-01', '--steps', '2']), 0)
        load.assert_called_once_with('2026-01-01')
        self.assertIn('relative_energy_change', str(stdout.write.call_args_list))

    def test_older_python_rejects_incompatible_bindings(self):
        for python in ((3, 10), (3, 11)):
            for pyside in ('6.12.0', '6.12.1'):
                with self.subTest(python=python, pyside=pyside):
                    error = desktop_compatibility_error(python, pyside)
                    self.assertIn('reference counts', error)
                    self.assertIn('python -m pip install -e .', error)

    def test_compatible_bindings_are_allowed(self):
        for python, pyside in (((3, 10), '6.11.2'), ((3, 11), '6.7.3'),
                               ((3, 12), '6.12.0'), ((3, 13), '6.12.1')):
            with self.subTest(python=python, pyside=pyside):
                self.assertIsNone(desktop_compatibility_error(python, pyside))

    def test_incompatible_install_exits_before_importing_qt(self):
        with patch('importlib.metadata.version', return_value='6.12.0'), \
             patch('sys.version_info', (3, 10, 12)), \
             patch('sys.stderr') as stderr:
            self.assertEqual(main([]), 1)
            self.assertIn('reference counts', str(stderr.write.call_args_list))


@unittest.skipUnless(importlib.util.find_spec('PySide6'), 'PySide6 is not installed')
class NativeBindingTests(unittest.TestCase):
    def test_repeated_qt_calls_preserve_python_singletons(self):
        # Isolate native failures from the test runner. No OpenGL or display is needed.
        script = textwrap.dedent('''
            import sys
            from PySide6.QtCore import QObject, Qt, Signal
            from PySide6.QtWidgets import QApplication, QWidget

            class Emitter(QObject):
                changed = Signal()

            app = QApplication([])
            widget = QWidget()
            emitter = Emitter()
            for _ in range(10):
                widget.setCursor(Qt.CursorShape.OpenHandCursor)
                emitter.changed.emit()
            before_none = sys.getrefcount(None)
            before_true = sys.getrefcount(True)
            for _ in range(100):
                widget.setCursor(Qt.CursorShape.OpenHandCursor)
                emitter.changed.emit()
            none_change = sys.getrefcount(None) - before_none
            true_change = sys.getrefcount(True) - before_true
            assert none_change >= -10, f'Qt leaked None references: {none_change}'
            assert true_change >= -10, f'Qt leaked True references: {true_change}'
        ''')
        result = subprocess.run(
            [sys.executable, '-c', script],
            env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'},
            capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
