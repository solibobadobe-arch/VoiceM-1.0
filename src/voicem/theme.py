"""Чёрно-зелёная тема VoiceM."""

BLACK = "#050A07"
PANEL = "#0B1410"
PANEL_LIGHT = "#12201A"
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
QFrame#panel {{
    background-color: {PANEL};
    border: 1px solid {GREEN_DEEP};
    border-radius: 14px;
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
QPushButton {{
    background-color: {PANEL_LIGHT};
    border: 1px solid {GREEN_DEEP};
    border-radius: 8px;
    padding: 6px 14px;
    color: {TEXT};
}}
QPushButton:hover {{
    border-color: {GREEN};
    color: {GREEN};
}}
QMenu {{
    background-color: {PANEL};
    border: 1px solid {GREEN_DEEP};
    padding: 6px;
}}
QMenu::item {{
    padding: 6px 22px;
    border-radius: 6px;
}}
QMenu::item:selected {{
    background-color: {GREEN_DEEP};
    color: {TEXT};
}}
"""
