from ..theme import COLORS as c

STYLE = f"""
QMainWindow, QWidget {{ background: {c['window']}; color: {c['text']}; font-family: 'DejaVu Sans', 'Segoe UI', sans-serif; font-size: 12px; }}
QLabel {{ background: transparent; }}
QWidget#header {{ background: {c['window']}; border-bottom: 1px solid {c['border']}; }}
QLabel#brand {{ font-size: 21px; font-weight: 600; letter-spacing: 5px; color: {c['text']}; }}
QLabel#subtitle {{ color: {c['secondary']}; font-size: 11px; }}
QLabel#eyebrow {{ color: {c['muted']}; font-size: 10px; letter-spacing: 2px; }}
QLabel#title {{ font-size: 25px; color: {c['text']}; }}
QLabel#metric {{ font-size: 16px; color: {c['text']}; }}
QLabel#muted {{ color: {c['muted']}; }}
QLabel#source {{ color: {c['secondary']}; font-size: 11px; }}
QFrame#panel {{ background: {c['panel']}; }}
QFrame#transport {{ border-top: 1px solid {c['border']}; background: {c['window']}; }}
QPushButton {{ background: {c['button']}; color: {c['secondary']}; border: 1px solid {c['border_control']}; padding: 7px 11px; border-radius: 5px; }}
QPushButton:hover {{ background: {c['button_hover']}; color: {c['text']}; border-color: {c['selection_border']}; }}
QPushButton:pressed {{ background: {c['button_pressed']}; }}
QPushButton:checked {{ color: {c['text']}; background: {c['button_hover']}; border-color: {c['accent']}; }}
QPushButton:disabled {{ color: {c['disabled']}; background: {c['panel_alt']}; border-color: {c['border']}; }}
QPushButton#primary {{ background: {c['button_primary']}; color: {c['text']}; border-color: {c['selection_border']}; font-weight: 600; }}
QPushButton#primary:hover {{ background: {c['button_primary_hover']}; border-color: {c['accent']}; }}
QPushButton#primary:pressed {{ background: {c['button_pressed']}; }}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateTimeEdit {{ background: {c['field']}; border: 1px solid {c['border_control']}; border-radius: 4px; padding: 6px; selection-background-color: {c['button_hover']}; selection-color: {c['text']}; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateTimeEdit:focus {{ border-color: {c['selection_border']}; }}
QComboBox QAbstractItemView {{ background: {c['panel_alt']}; color: {c['secondary']}; selection-background-color: {c['button']}; selection-color: {c['text']}; }}
QListWidget {{ background: {c['panel']}; border: none; outline: none; }}
QListWidget::item {{ padding: 14px 10px; border: 1px solid transparent; border-radius: 4px; margin: 2px; color: {c['secondary']}; }}
QListWidget::item:selected {{ background: {c['button']}; color: {c['text']}; border-color: {c['selection_border']}; }}
QListWidget::item:hover {{ background: {c['button_hover']}; }}
QCheckBox {{ background: transparent; spacing: 8px; padding: 4px 0; color: {c['secondary']}; }}
QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid {c['disabled']}; border-radius: 3px; background: {c['panel_alt']}; }}
QCheckBox::indicator:checked {{ background: {c['selection_border']}; border-color: {c['accent']}; }}
QCheckBox::indicator:hover {{ border-color: {c['accent_soft']}; }}
QSlider::groove:horizontal {{ height: 5px; background: {c['field']}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {c['button_hover']}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {c['secondary']}; border: 1px solid {c['selection_border']}; width: 13px; margin: -5px 0; border-radius: 7px; }}
QSlider::handle:horizontal:hover {{ background: {c['text']}; }}
QSplitter::handle {{ background: {c['border']}; width: 1px; }}
QStatusBar {{ background: {c['window']}; color: {c['muted']}; font-size: 11px; }}
QToolTip {{ background: {c['panel_alt']}; color: {c['text']}; border: 1px solid {c['selection_border']}; padding: 6px; }}
QProgressBar {{ background: {c['field']}; border: 1px solid {c['border_control']}; border-radius: 3px; max-height: 8px; }}
QProgressBar::chunk {{ background: {c['selection_border']}; }}
QMenuBar {{ background: {c['window']}; color: {c['secondary']}; }}
QMenuBar::item:selected, QMenu::item:selected {{ background: {c['button_hover']}; color: {c['text']}; }}
QMenu {{ background: {c['panel']}; color: {c['secondary']}; border: 1px solid {c['border_control']}; }}
QScrollArea {{ border: none; }}
QScrollBar:vertical {{ background: {c['window']}; width: 8px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {c['border_control']}; min-height: 25px; border-radius: 4px; }}
QScrollBar::handle:vertical:hover {{ background: {c['selection_border']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; border: none; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{ background: {c['window']}; height: 8px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: {c['border_control']}; min-width: 25px; border-radius: 4px; }}
QScrollBar::handle:horizontal:hover {{ background: {c['selection_border']}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; border: none; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}
"""
