STYLE = """
QMainWindow, QWidget { background: #101722; color: #dce4ef; font-family: 'DejaVu Sans', 'Segoe UI', sans-serif; font-size: 12px; }
QWidget#header { background: #111b29; border-bottom: 1px solid #2a3546; }
QLabel#brand { font-size: 21px; font-weight: 600; letter-spacing: 5px; color: #efc596; }
QLabel#subtitle { color: #8799b2; font-size: 11px; }
QLabel#eyebrow { color: #d4ad80; font-size: 10px; letter-spacing: 2px; }
QLabel#title { font-size: 25px; color: #f0d7b6; }
QLabel#metric { font-size: 16px; color: #dce8f5; }
QLabel#muted { color: #91a2b9; }
QLabel#source { color: #d4bc92; font-size: 11px; }
QFrame#panel { background: #111b29; }
QFrame#transport { border-top: 1px solid #2a3546; background: #111b29; }
QPushButton { background: #1c2a3d; border: 1px solid #344258; padding: 7px 11px; border-radius: 5px; }
QPushButton:hover { background: #2a3b51; border-color: #8e9db0; }
QPushButton:pressed { background: #354c67; }
QPushButton:checked { color: #f2d0a6; border-color: #bf976a; }
QPushButton:disabled { color: #5f7088; border-color: #293547; }
QPushButton#primary { background: #dab17f; color: #162030; border-color: #dab17f; font-weight: 600; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateTimeEdit { background: #0d1521; border: 1px solid #334055; border-radius: 4px; padding: 6px; selection-background-color: #63503e; }
QComboBox QAbstractItemView { background: #172538; selection-background-color: #354b65; }
QListWidget { background: #111b29; border: none; outline: none; }
QListWidget::item { padding: 14px 10px; border-radius: 4px; margin: 2px; }
QListWidget::item:selected { background: #293a50; color: #f0d0a6; }
QListWidget::item:hover { background: #1a2a3e; }
QCheckBox { spacing: 8px; padding: 4px 0; }
QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #5d6e84; border-radius: 3px; background: #162132; }
QCheckBox::indicator:checked { background: #dab17f; border-color: #dab17f; }
QSplitter::handle { background: #273346; width: 1px; }
QStatusBar { background: #0d1420; color: #8fa3bc; font-size: 11px; }
QToolTip { background: #24364b; color: #edf1f6; border: 1px solid #647a94; padding: 6px; }
QProgressBar { background: #0d1521; border: 1px solid #334055; border-radius: 3px; max-height: 8px; }
QProgressBar::chunk { background: #dab17f; }
QMenuBar { background: #111b29; }
QMenuBar::item:selected, QMenu::item:selected { background: #2a3b51; }
QMenu { background: #152132; border: 1px solid #334055; }
QScrollArea { border: none; }
"""
