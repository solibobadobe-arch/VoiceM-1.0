"""Кастомные виджеты VoiceM в чёрно-зелёном стиле."""
from __future__ import annotations

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from . import theme


class ToggleSwitch(QWidget):
    """Ползунок-переключатель с плавной анимацией."""

    toggled = Signal(bool)

    def __init__(self, checked: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self._checked = bool(checked)
        self._offset = 1.0 if checked else 0.0
        self.setFixedSize(52, 28)
        self.setCursor(Qt.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    # -- анимируемое свойство ------------------------------
    def get_offset(self) -> float:
        return self._offset

    def set_offset(self, value: float) -> None:
        self._offset = float(value)
        self.update()

    offset = Property(float, get_offset, set_offset)

    # -- API -------------------------------------------------------
    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool, animate: bool = True) -> None:
        checked = bool(checked)
        if checked == self._checked:
            return
        self._checked = checked
        if animate:
            self._anim.stop()
            self._anim.setStartValue(self._offset)
            self._anim.setEndValue(1.0 if checked else 0.0)
            self._anim.start()
        else:
            self.set_offset(1.0 if checked else 0.0)

    def mousePressEvent(self, event) -> None:  # noqa: ANN001
        if event.button() == Qt.LeftButton:
            self.setChecked(not self._checked)
            self.toggled.emit(self._checked)
        super().mousePressEvent(event)

    # -- отрисовка ---------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: ANN001
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        track = QRectF(1, 4, self.width() - 2, self.height() - 8)
        off_color = QColor(theme.PANEL_LIGHT)
        on_color = QColor(theme.GREEN_DEEP)
        color = QColor(
            int(off_color.red() + (on_color.red() - off_color.red()) * self._offset),
            int(off_color.green() + (on_color.green() - off_color.green()) * self._offset),
            int(off_color.blue() + (on_color.blue() - off_color.blue()) * self._offset),
        )
        painter.setPen(QPen(QColor(theme.GREEN if self._checked else theme.BORDER), 1))
        painter.setBrush(color)
        painter.drawRoundedRect(track, track.height() / 2, track.height() / 2)

        knob_size = 18.0
        travel = self.width() - knob_size - 10
        x = 5 + travel * self._offset
        y = (self.height() - knob_size) / 2
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(theme.GREEN if self._checked else theme.TEXT_DIM))
        painter.drawEllipse(QRectF(x, y, knob_size, knob_size))
        painter.end()


class Card(QFrame):
    """Карточка-контейнер для группы настроек."""

    def __init__(self, title: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(18, 16, 18, 16)
        self._layout.setSpacing(12)

        if title:
            label = QLabel(title)
            label.setObjectName("cardTitle")
            self._layout.addWidget(label)

    def body(self) -> QVBoxLayout:
        return self._layout

    def add_row(self, title: str, subtitle: str, control: QWidget) -> QWidget:
        """Строка: заголовок + пояснение слева, управление справа."""
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        name = QLabel(title)
        name.setObjectName("rowTitle")
        text_box.addWidget(name)
        if subtitle:
            hint = QLabel(subtitle)
            hint.setObjectName("rowHint")
            hint.setWordWrap(True)
            text_box.addWidget(hint)

        layout.addLayout(text_box, 1)
        layout.addWidget(control, 0, Qt.AlignRight | Qt.AlignVCenter)
        self._layout.addWidget(row)
        return row


class StatusDot(QLabel):
    """Цветной индикатор состояния доступа."""

    def __init__(self, ok: bool | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self._ok = ok

    def set_state(self, ok: bool | None) -> None:
        self._ok = ok
        self.update()

    def paintEvent(self, event) -> None:  # noqa: ANN001
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        if self._ok is True:
            color = QColor(theme.GREEN)
        elif self._ok is False:
            color = QColor(theme.ERROR)
        else:
            color = QColor(theme.WARN)
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(1, 1, 10, 10)
        painter.end()
