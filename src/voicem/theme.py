"""Чёрно-зелёная тема VoiceM."""

BLACK = "#050A07"
PANEL = "#0B1410"
PANEL_LIGHT = "#12201A"
DRAWER = "#08120D"
BORDER = "#173C29"
GREEN = "#2BE07A"
GREEN_DIM = "#1B9A55"
GREEN_DEEP = "#0F5F36"
TEXT = "#DFF7E6"
TEXT_DIM = "#8FBFA2"
WARN = "#FFC65C"
ERROR = "#FF6B6B"

QSS = f"""
QWidget {{
    background-color: {BLACK};
    color: {TEXT};
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}}

/* --- шапка --- */
QWidget#topBar {{
    background-color: {PANEL};
    border-bottom: 1px solid {BORDER};
}}
QLabel#appTitle {{
    color: {TEXT};
    font-size: 16px;
    font-weight: 700;
}}
QLabel#appSubtitle {{
    color: {TEXT_DIM};
    font-size: 11px;
}}
QPushButton#burger {{
    background: transparent;
    border: 1px solid {BORDER};
    border-radius: 10px;
    min-width: 40px;
    min-height: 40px;
}}
QPushButton#burger:hover {{
    border-color: {GREEN};
    background-color: {PANEL_LIGHT};
}}

/* --- боковая менюшка --- */
QWidget#drawer {{
    background-color: {DRAWER};
    border-right: 1px solid {GREEN_DEEP};
}}
QLabel#drawerTitle {{
    color: {GREEN};
    font-size: 15px;
    font-weight: 700;
    padding: 4px 8px;
}}
QLabel#drawerHint {{
    color: {TEXT_DIM};
    font-size: 10px;
    padding: 4px 10px;
}}
QPushButton#navItem {{
    background: transparent;
    border: none;
    border-radius: 10px;
    padding: 11px 14px;
    text-align: left;
    color: {TEXT_DIM};
    font-size: 13px;
}}
QPushButton#navItem:hover {{
    background-color: {PANEL_LIGHT};
    color: {TEXT};
}}
QPushButton#navItem:checked {{
    background-color: {GREEN_DEEP};
    color: {TEXT};
    font-weight: 600;
}}

/* --- карточки --- */
QFrame#card {{
    background-color: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 14px;
}}
QFrame#card:hover {{
    border-color: {GREEN_DEEP};
}}
QLabel#cardTitle {{
    color: {GREEN};
    font-size: 13px;
    font-weight: 700;
}}
QLabel#rowTitle {{
    color: {TEXT};
    font-size: 13px;
}}
QLabel#rowHint {{
    color: {TEXT_DIM};
    font-size: 11px;
}}
QLabel#pageTitle {{
    color: {TEXT};
    font-size: 20px;
    font-weight: 700;
}}
QLabel#pageHint {{
    color: {TEXT_DIM};
    font-size: 12px;
}}
QLabel#status {{
    color: {GREEN};
    font-size: 13px;
    font-weight: 600;
}}
QLabel#hint {{
    color: {TEXT_DIM};
    font-size: 11px;
}}
QLabel#bigHotkey {{
    color: {GREEN};
    font-size: 30px;
    font-weight: 800;
}}

/* --- кнопки --- */
QPushButton {{
    background-color: {PANEL_LIGHT};
    border: 1px solid {BORDER};
    border-radius: 9px;
    padding: 7px 16px;
    color: {TEXT};
}}
QPushButton:hover {{
    border-color: {GREEN};
    color: {GREEN};
}}
QPushButton:pressed {{
    background-color: {GREEN_DEEP};
}}
QPushButton#primary {{
    background-color: {GREEN_DEEP};
    border: 1px solid {GREEN};
    color: {TEXT};
    font-weight: 600;
}}
QPushButton#primary:hover {{
    background-color: {GREEN_DIM};
}}

/* --- поля --- */
QComboBox, QLineEdit, QSpinBox {{
    background-color: {PANEL_LIGHT};
    border: 1px solid {BORDER};
    border-radius: 9px;
    padding: 6px 10px;
    min-width: 150px;
    color: {TEXT};
}}
QComboBox:hover, QLineEdit:hover {{
    border-color: {GREEN_DEEP};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background-color: {PANEL};
    border: 1px solid {GREEN_DEEP};
    selection-background-color: {GREEN_DEEP};
    color: {TEXT};
    outline: none;
}}
QTextEdit, QListWidget {{
    background-color: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 8px;
    color: {TEXT};
}}
QListWidget::item {{
    padding: 8px;
    border-radius: 8px;
}}
QListWidget::item:selected {{
    background-color: {GREEN_DEEP};
    color: {TEXT};
}}

/* --- скролл --- */
QScrollArea {{
    border: none;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 4px;
}}
QScrollBar::handle:vertical {{
    background: {GREEN_DEEP};
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {GREEN_DIM};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* --- меню трея --- */
QMenu {{
    background-color: {PANEL};
    border: 1px solid {GREEN_DEEP};
    padding: 6px;
}}
QMenu::item {{
    padding: 7px 24px;
    border-radius: 6px;
}}
QMenu::item:selected {{
    background-color: {GREEN_DEEP};
    color: {TEXT};
}}
QToolTip {{
    background-color: {PANEL};
    color: {TEXT};
    border: 1px solid {GREEN_DEEP};
    padding: 5px;
}}
"""
