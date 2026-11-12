from datetime import datetime
import json
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread
from time import monotonic

import numpy as np
from PySide6.QtCore import QDate, QDateTime, QSettings, QSize, QStandardPaths, Qt, QTime, QTimer
from PySide6.QtGui import QAction, QColor, QIcon, QKeySequence, QPainter, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDateTimeEdit, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QProgressBar,
    QPushButton, QScrollArea, QSlider, QSplitter, QVBoxLayout, QWidget,
)

from ..data.catalog import AU, BODIES, DAY
from ..data.horizons import Cancelled, HorizonsClient, HorizonsError
from ..data.scenario import demo_scenario
from ..physics.runner import SimulationRunner
from ..rendering.viewport import Viewport
from .style import STYLE


def label(text, name=None):
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(True)
    return widget


def button(text, callback, tooltip=None):
    widget = QPushButton(text)
    widget.clicked.connect(callback)
    if tooltip:
        widget.setToolTip(tooltip)
    return widget


def body_icon(body):
    pixmap = QPixmap(24,24)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(body.color))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(5,5,14,14)
    painter.end()
    return QIcon(pixmap)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Orbital · Solar System Simulator')
        self.setMinimumSize(980, 660)
        self.resize(1440, 900)
        self.setStyleSheet(STYLE)
        self.settings = QSettings('Aamir2020', 'SolarSystemSimulator2')
        self.scenario = demo_scenario()
        self.runner = SimulationRunner(self.scenario.state)
        self.view = Viewport()
        self.loading_thread = None
        self.load_cancel = Event()
        self.load_messages = Queue()
        self.load_token = 0
        self.last_inspector = 0
        self.setCentralWidget(self._build())
        self._menus()
        self.view.selected.connect(self._select_from_view)
        self.view.followed.connect(self._follow_changed)
        self.view.graphics_error.connect(self._graphics_error)
        self.body_list.setCurrentRow(0)
        self._restore_settings()
        self._show_source()
        self.statusBar().showMessage('Offline educational demo loaded. Choose a TDB date and Load NASA for real initial conditions.')
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._tick)
        self.timer.start()

    def _build(self):
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        header = QWidget()
        header.setObjectName('header')
        row = QHBoxLayout(header)
        row.setContentsMargins(24,18,24,18)
        row.addWidget(label('◉ ORBITAL', 'brand'))
        row.addWidget(label('SOLAR SYSTEM SIMULATOR  /  PYTHON N-BODY', 'subtitle'))
        row.addStretch()
        self.pause_badge = label('● PAUSED', 'eyebrow')
        row.addWidget(self.pause_badge)
        row.addSpacing(18)
        row.addWidget(button('Help  ?', self._help))
        layout.addWidget(header)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self._body_panel())
        self.splitter.addWidget(self.view)
        self.inspector = self._inspector_panel()
        self.splitter.addWidget(self.inspector)
        self.splitter.setStretchFactor(1,1)
        self.splitter.setSizes([205,940,285])
        layout.addWidget(self.splitter,1)
        layout.addWidget(self._transport())
        return root

    def _body_panel(self):
        panel = QFrame()
        panel.setObjectName('panel')
        panel.setMinimumWidth(160)
        panel.setMaximumWidth(270)
        column = QVBoxLayout(panel)
        column.setContentsMargins(16,22,16,18)
        column.addWidget(label('EXPLORER', 'eyebrow'))
        self.search = QLineEdit()
        self.search.setPlaceholderText('Find a planet…')
        self.search.setAccessibleName('Search celestial bodies')
        self.search.textChanged.connect(self._filter_bodies)
        column.addWidget(self.search)
        self.body_list = QListWidget()
        self.body_list.setAccessibleName('Celestial bodies')
        self.body_list.setIconSize(QSize(24,24))
        for body in BODIES:
            item = QListWidgetItem(body_icon(body), body.name)
            self.body_list.addItem(item)
        self.body_list.currentRowChanged.connect(self._select_from_list)
        self.body_list.itemDoubleClicked.connect(lambda item: self.view.focus_body(self.body_list.row(item)))
        column.addWidget(self.body_list,1)
        column.addWidget(label('CAMERA', 'eyebrow'))
        self.camera_choice = QComboBox()
        self.camera_choice.addItems(['Inner system','Outer system','Whole system','Selected'])
        self.camera_choice.activated.connect(lambda _: self.view.preset(self.camera_choice.currentText()))
        self.camera_choice.setAccessibleName('Camera preset')
        column.addWidget(self.camera_choice)
        self.follow_button = button('Follow selected', self._toggle_follow,
                                    'Keep the camera centered on the selected body (F)')
        self.follow_button.setCheckable(True)
        column.addWidget(self.follow_button)
        column.addWidget(button('Reset camera  H', lambda: self.view.preset('Inner system')))
        column.addSpacing(14)
        column.addWidget(label('Scroll to zoom\nDrag to pan\nDouble click to follow', 'muted'))
        return panel

    def _inspector_panel(self):
        panel = QFrame()
        panel.setObjectName('panel')
        panel.setMinimumWidth(235)
        panel.setMaximumWidth(340)
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(0,0,0,0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        column = QVBoxLayout(inner)
        column.setContentsMargins(22,22,22,18)
        column.setSpacing(12)
        column.addWidget(label('BODY INSPECTOR', 'eyebrow'))
        self.body_name = label('Sun', 'title')
        column.addWidget(self.body_name)
        self.metrics = {}
        for key in ('Mass','Radius','Speed · barycentric','Distance from Sun','X · barycentric','Y · barycentric'):
            column.addWidget(label(key.upper(), 'eyebrow'))
            metric = label('—','metric')
            self.metrics[key] = metric
            column.addWidget(metric)
        column.addWidget(button('Focus on body', self._focus_selection))
        column.addSpacing(18)
        column.addWidget(label('DISPLAY', 'eyebrow'))
        self.toggles = {}
        for title, attribute in [('Body labels','labels'),('Orbit trails','trails'),
                                  ('Background stars','stars'),('Lighting & rings','effects'),
                                  ('Physical planet radii','physical')]:
            check = QCheckBox(title)
            check.setChecked(getattr(self.view,attribute))
            check.toggled.connect(lambda value, attr=attribute: setattr(self.view,attr,value))
            self.toggles[attribute] = check
            column.addWidget(check)
        column.addWidget(label('Trail history (maximum 1,500 samples)', 'muted'))
        self.trail_slider = QSlider(Qt.Orientation.Horizontal)
        self.trail_slider.setRange(50,1500)
        self.trail_slider.setValue(800)
        self.trail_slider.setAccessibleName('Trail history length')
        self.trail_slider.valueChanged.connect(lambda value: setattr(self.view,'trail_length',value))
        column.addWidget(self.trail_slider)
        column.addWidget(button('Save screenshot…', self._screenshot))
        column.addSpacing(12)
        column.addWidget(label('REFERENCE FRAME', 'eyebrow'))
        column.addWidget(label('ICRF / ecliptic J2000\nSolar-system barycenter\n2D projection · SI physics', 'muted'))
        column.addStretch()
        scroll.setWidget(inner)
        outer.addWidget(scroll)
        return panel

    def _transport(self):
        panel = QFrame()
        panel.setObjectName('transport')
        column = QVBoxLayout(panel)
        column.setContentsMargins(20,14,20,14)
        controls = QHBoxLayout()
        self.play_button = button('▶  Play', self._toggle_play, 'Pause/play (Space)')
        self.play_button.setObjectName('primary')
        controls.addWidget(self.play_button)
        controls.addWidget(button('Step', self._step, 'Advance one integration timestep (N)'))
        controls.addWidget(button('Restart', self._restart, 'Return to the loaded initial conditions (R)'))
        controls.addSpacing(12)
        controls.addWidget(label('SPEED', 'eyebrow'))
        self.speed = QComboBox()
        for text, days in [('1 day / sec',1),('10 days / sec',10),('30 days / sec',30),
                           ('100 days / sec',100),('1 year / sec',365.25),('10 years / sec',3652.5)]:
            self.speed.addItem(text, days*DAY)
        self.speed.setCurrentIndex(2)
        self.speed.currentIndexChanged.connect(self._configure)
        self.speed.setAccessibleName('Playback speed')
        controls.addWidget(self.speed)
        controls.addWidget(label('STEP', 'eyebrow'))
        self.timestep = QComboBox()
        for text, seconds in [('1 hour',3600),('6 hours',21600),('1 day',DAY)]:
            self.timestep.addItem(text,seconds)
        self.timestep.setCurrentIndex(2)
        self.timestep.currentIndexChanged.connect(self._configure)
        self.timestep.setToolTip('Numerical integration timestep; independent of playback speed')
        self.timestep.setAccessibleName('Integration timestep')
        controls.addWidget(self.timestep)
        controls.addStretch()
        self.sim_date = label('2026-01-01 00:00 TDB','metric')
        controls.addWidget(self.sim_date)
        column.addLayout(controls)
        row = QHBoxLayout()
        row.addWidget(label('INITIAL DATE · TDB', 'eyebrow'))
        self.date = QDateTimeEdit()
        # This is a TDB calendar input, not a conversion from local/UTC clock time.
        self.date.setDisplayFormat('yyyy-MM-dd HH:mm:ss')
        self.date.setCalendarPopup(True)
        self.date.setDateTime(QDateTime(QDate(2026,1,1),QTime(0,0,0)))
        self.date.setMinimumDateTime(QDateTime(QDate(1900,1,1),QTime(0,0,0)))
        self.date.setMaximumDateTime(QDateTime(QDate(2100,12,31),QTime(23,59,59)))
        self.date.setToolTip('TDB calendar date. No local timezone or UTC conversion is applied.')
        row.addWidget(self.date)
        self.load_button = button('Load NASA', self._load_nasa)
        row.addWidget(self.load_button)
        self.cancel_button = button('Cancel', self._cancel_load)
        self.cancel_button.setVisible(False)
        row.addWidget(self.cancel_button)
        row.addWidget(button('Offline demo', self._load_demo))
        self.progress = QProgressBar()
        self.progress.setRange(0,9)
        self.progress.setTextVisible(False)
        self.progress.setMaximumWidth(85)
        self.progress.hide()
        row.addWidget(self.progress)
        row.addStretch()
        self.source_label = label('', 'source')
        self.source_label.setMaximumWidth(400)
        row.addWidget(self.source_label)
        column.addLayout(row)
        return panel

    def _menus(self):
        def action(menu, title, shortcut, callback, checkable=False):
            item = QAction(title,self)
            if shortcut:
                item.setShortcut(QKeySequence(shortcut))
            item.setCheckable(checkable)
            item.triggered.connect(callback)
            menu.addAction(item)
            return item
        simulation = self.menuBar().addMenu('Simulation')
        action(simulation,'Play / pause','Space',self._toggle_play)
        action(simulation,'Single step','N',self._step)
        action(simulation,'Restart','R',self._restart)
        action(simulation,'Save screenshot…','Ctrl+S',self._screenshot)
        action(simulation,'Quit','Ctrl+Q',self.close)
        view = self.menuBar().addMenu('View')
        action(view,'Home camera','H',lambda: self.view.preset('Inner system'))
        action(view,'Follow selection','F',self._toggle_follow)
        action(view,'Fullscreen','F11',self._fullscreen)
        item = action(view,'Show inspector','I',self._toggle_inspector,True)
        item.setChecked(True)
        self.inspector_action = item
        help_menu = self.menuBar().addMenu('Help')
        action(help_menu,'Controls and scientific limits','F1',self._help)

    def _restore_settings(self):
        for name, check in self.toggles.items():
            value = self.settings.value(f'display/{name}', check.isChecked(), type=bool)
            check.setChecked(value)
        self.trail_slider.setValue(self.settings.value('display/trail_length',800,type=int))
        geometry = self.settings.value('window/geometry')
        if geometry is not None:
            self.restoreGeometry(geometry)

    def _filter_bodies(self, text):
        for i,body in enumerate(BODIES):
            self.body_list.item(i).setHidden(text.casefold() not in body.name.casefold())

    def _select_from_list(self, index):
        if index >= 0:
            self.view.set_selection(index)
            self._update_inspector()

    def _select_from_view(self, index):
        self.body_list.blockSignals(True)
        self.body_list.setCurrentRow(-1 if index is None else index)
        self.body_list.blockSignals(False)
        self._update_inspector()

    def _follow_changed(self, enabled):
        self.follow_button.setChecked(enabled)
        self.follow_button.setText('Following selected' if enabled else 'Follow selected')

    def _toggle_follow(self):
        self.view.set_follow(not self.view.follow)

    def _focus_selection(self):
        if self.view.selection is not None:
            self.view.focus_body(self.view.selection)

    def _configure(self):
        self.runner.configure(rate=float(self.speed.currentData()), dt=float(self.timestep.currentData()))

    def _set_paused(self, paused):
        self.runner.configure(paused=paused)
        self.view.paused = paused
        self.play_button.setText('▶  Play' if paused else 'Ⅱ  Pause')
        self.pause_badge.setText('● PAUSED' if paused else '● RUNNING')

    def _toggle_play(self):
        self._set_paused(not self.view.paused)

    def _step(self):
        self._set_paused(True)
        self.runner.single_step()

    def _restart(self):
        self._set_paused(True)
        self.runner.reset(self.scenario.state)
        self.statusBar().showMessage('Restarted at the loaded initial epoch.')

    def _replace_scenario(self, scenario):
        self._set_paused(True)
        self.scenario = scenario
        self.runner.reset(scenario.state)
        self.view.set_follow(False)
        self.view.preset('Inner system')
        self._show_source()

    def _load_demo(self):
        self._cancel_load()
        self._replace_scenario(demo_scenario())
        self.statusBar().showMessage('Synthetic circular-orbit demo loaded. These are not NASA ephemerides.')

    def _show_source(self):
        self.source_label.setText(self.scenario.source)
        self.source_label.setToolTip(self.scenario.source + '\nInitial epoch: ' + self.scenario.epoch + ' TDB')

    def _load_nasa(self):
        if self.loading_thread and self.loading_thread.is_alive():
            self.statusBar().showMessage('Waiting for the previous NASA request to finish cancelling…')
            return
        self._set_paused(True)
        self.load_cancel = Event()
        self.load_token += 1
        token, cancel, messages = self.load_token, self.load_cancel, self.load_messages
        epoch = self.date.dateTime().toString('yyyy-MM-ddTHH:mm:ss')
        cache = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation)) / 'horizons'
        def work():
            try:
                result = HorizonsClient(cache).load(epoch,
                    progress=lambda n,text: messages.put((token,'progress',(n,text))), cancel=cancel)
                messages.put((token,'loaded',result))
            except (HorizonsError, OSError, ValueError) as exc:
                messages.put((token,'cancelled' if isinstance(exc,Cancelled) else 'error',str(exc)))
        self.loading_thread = Thread(target=work,name='nasa-horizons-loader',daemon=True)
        self.load_button.setEnabled(False)
        self.cancel_button.show()
        self.progress.show()
        self.progress.setValue(0)
        self.loading_thread.start()

    def _cancel_load(self):
        if self.loading_thread and self.loading_thread.is_alive():
            self.load_cancel.set()
            self.statusBar().showMessage('Cancelling NASA loading; the current request may need its timeout to finish.')
        self.load_token += 1
        self._loading_finished()

    def _loading_finished(self):
        self.load_button.setEnabled(True)
        self.cancel_button.hide()
        self.progress.hide()

    def _tick(self):
        snapshot = self.runner.latest()
        if snapshot is not None:
            self.view.accept_snapshot(snapshot)
            self.sim_date.setText(self.scenario.date_at(snapshot.elapsed))
        try:
            error = self.runner.errors.get_nowait()
            self._set_paused(True)
            self.statusBar().showMessage(error)
        except Empty:
            pass
        while True:
            try:
                token,kind,value = self.load_messages.get_nowait()
            except Empty:
                break
            if token != self.load_token:
                continue
            if kind == 'progress':
                self.progress.setValue(value[0])
                self.statusBar().showMessage(value[1])
            elif kind == 'loaded':
                self._loading_finished()
                self._replace_scenario(value)
                self.statusBar().showMessage('NASA initial conditions loaded. Press Play to integrate locally.')
            else:
                self._loading_finished()
                self.statusBar().showMessage(value)
                if kind == 'error':
                    QMessageBox.warning(self,'NASA loading failed',
                        value+'\n\nThe current scenario is retained. Retry, or use the labeled offline demo.')
        if monotonic()-self.last_inspector > .15:
            self._update_inspector()
            self.last_inspector = monotonic()
        self.view.update()

    def _update_inspector(self):
        index = self.view.selection
        snapshot = self.view.snapshot
        if index is None:
            self.body_name.setText('Select a body')
            for metric in self.metrics.values():
                metric.setText('—')
            return
        body = BODIES[index]
        self.body_name.setText(body.name)
        self.metrics['Mass'].setText(f'{body.mass:.4g} kg')
        self.metrics['Radius'].setText(f'{body.radius/1000:,.0f} km')
        if snapshot is not None:
            position = snapshot.positions[index]
            values = {'Speed · barycentric': f'{np.linalg.norm(snapshot.velocities[index])/1000:,.3f} km/s',
                      'Distance from Sun': f'{np.linalg.norm(position-snapshot.positions[0])/AU:,.5f} AU',
                      'X · barycentric': f'{position[0]/AU:+,.6f} AU',
                      'Y · barycentric': f'{position[1]/AU:+,.6f} AU'}
            for key,value in values.items():
                self.metrics[key].setText(value)
        self.follow_button.setEnabled(index is not None)

    def _graphics_error(self, message):
        self._set_paused(True)
        self.statusBar().showMessage(message)

    def _fullscreen(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def _toggle_inspector(self, checked):
        self.inspector.setVisible(checked)

    def _screenshot(self):
        if self.view.error or self.view.ctx is None:
            QMessageBox.warning(self,'Screenshot unavailable','A working OpenGL context is required.')
            return
        path,_ = QFileDialog.getSaveFileName(self,'Save simulation screenshot',
                    f'orbital-{datetime.now():%Y%m%d-%H%M%S}.png','PNG images (*.png)')
        if not path:
            return
        if not path.lower().endswith('.png'):
            path += '.png'
        if not self.view.grabFramebuffer().save(path):
            QMessageBox.warning(self,'Screenshot failed','The image could not be saved.')
            return
        try:
            metadata = {'source':self.scenario.source,'initial_epoch_tdb':self.scenario.epoch,
                        'simulation_seconds':self.view.snapshot.elapsed if self.view.snapshot else 0,
                        'frame':self.scenario.frame,'exaggerated_radii':not self.view.physical}
            Path(path).with_suffix('.json').write_text(json.dumps(metadata,indent=2)+'\n')
        except OSError:
            self.statusBar().showMessage(f'Screenshot saved to {path}; metadata could not be written.')
            return
        self.statusBar().showMessage(f'Screenshot and provenance saved to {path}')

    def _help(self):
        QMessageBox.information(self,'Orbital · Controls & model',
            'NAVIGATION\nScroll: zoom toward cursor · Drag: pan\nClick: inspect · Double click: focus and follow\n'
            'H: home · F: follow · I: inspector · F11: fullscreen\n\n'
            'SIMULATION\nSpace: play/pause · N: one step · R: restart\nCtrl+S: screenshot · F1: help\n\n'
            'SCIENCE\nNewtonian pairwise gravity and kick–drift–kick leapfrog. '
            'Two-dimensional projection; no moons, collisions, relativity, or planet rotation. '
            'The one-day timestep preserves the original baseline; choose smaller steps for convergence.\n\n'
            'NASA initializes the state; subsequent motion is integrated locally. '
            'Dates are TDB calendar dates, not your local clock. Masses are local constants. '
            'The offline demo uses synthetic circular orbits and is not NASA data. '
            'Trails show simulated history. Default radii are exaggerated.\n\n'
            'High playback rates may be limited by available compute. The numerical timestep '
            'does not change automatically. Arbitrary reverse playback is not implemented.')

    def closeEvent(self, event):
        self.timer.stop()
        self.load_cancel.set()
        self.runner.close()
        for name,check in self.toggles.items():
            self.settings.setValue(f'display/{name}',check.isChecked())
        self.settings.setValue('display/trail_length',self.trail_slider.value())
        self.settings.setValue('window/geometry',self.saveGeometry())
        super().closeEvent(event)
