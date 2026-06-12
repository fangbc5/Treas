"""屏幕取色器 - 精美的屏幕取色工具（先截图再遮罩，从快照取色）"""

import sys
import os
import colorsys

_project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QApplication, QSizePolicy, QLabel, QWidget,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt5.QtGui import QColor, QCursor, QPixmap, QPainter, QPen, QFont, QImage

from qfluentwidgets import (
    PushButton, PrimaryPushButton, LineEdit,
    StrongBodyLabel, CaptionLabel, TitleLabel,
    FluentIcon, InfoBar, InfoBarPosition, CardWidget,
    ToolButton,
)

from src.core.plugin_base import PluginBase
from AppKit import NSEvent, NSKeyDownMask


def rgb_to_hex(r, g, b):
    return f"#{r:02X}{g:02X}{b:02X}"


def rgb_to_hsl(r, g, b):
    r1, g1, b1 = r / 255, g / 255, b / 255
    h, l, s = colorsys.rgb_to_hls(r1, g1, b1)
    return round(h * 360), round(s * 100), round(l * 100)


def is_light_color(r, g, b):
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return luminance > 0.6


class MagnifierWidget(QLabel):
    def __init__(self):
        super().__init__(None, Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setFixedSize(144, 144)
        self._pixel_size = 16   # 每个格子的显示大小
        self._grid_size = 9     # 9x9格子
        self._snapshot = None

    def set_snapshot(self, snapshot):
        self._snapshot = snapshot

    def update_at(self, x, y, dpr=1.0):
        if self._snapshot is None:
            return
        # 逻辑坐标转物理像素
        px, py = int(x * dpr), int(y * dpr)
        half = self._grid_size // 2  # =4，中心是第5格(索引4)
        src_rect = QPixmap.fromImage(self._snapshot.copy(
            px - half, py - half, self._grid_size, self._grid_size
        ))
        logical_size = self._pixel_size * self._grid_size  # 144
        physical_size = int(logical_size * dpr)
        scaled = src_rect.scaled(
            physical_size, physical_size,
            Qt.IgnoreAspectRatio, Qt.FastTransformation,
        )
        scaled.setDevicePixelRatio(dpr)
        painter = QPainter(scaled)
        # 网格线（用逻辑坐标）
        ls = logical_size
        painter.setPen(QPen(QColor(255, 255, 255, 60), 1))
        for i in range(self._grid_size + 1):
            offset = i * self._pixel_size
            painter.drawLine(offset, 0, offset, ls)
            painter.drawLine(0, offset, ls, offset)
        # 中心格子（索引4）边框
        c = 4 * self._pixel_size
        ps = self._pixel_size
        painter.setPen(QPen(QColor(255, 0, 0), 2))
        painter.drawRect(c, c, ps, ps)
        painter.end()
        self.setPixmap(scaled)
        screen = QApplication.screenAt(QPoint(x, y))
        if not screen:
            screen = QApplication.primaryScreen()
        geo = screen.geometry()
        fx, fy = x + 20, y + 20
        if fx + 144 > geo.right():
            fx = x - 164
        if fy + 144 > geo.bottom():
            fy = y - 164
        self.move(fx, fy)

class PickOverlay(QWidget):
    color_picked = pyqtSignal(int, int, int)
    pick_cancelled = pyqtSignal()

    def __init__(self):
        super().__init__(None, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._snapshot_image = None
        self._magnifier = MagnifierWidget()
        self._current_color = (0, 0, 0)
        self._keyboard_monitor = None
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._on_tick)

    def start(self):
        screen = QApplication.primaryScreen()
        geo = screen.geometry()
        snapshot = screen.grabWindow(0, geo.x(), geo.y(), geo.width(), geo.height())
        self._snapshot_image = snapshot.toImage()
        self._dpr = screen.devicePixelRatio()
        self.setGeometry(geo)
        self._magnifier.set_snapshot(self._snapshot_image)
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self._magnifier.show()
        self._timer.start()
        self._keyboard_monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
            NSKeyDownMask, self._on_global_key
        )

    def stop(self):
        self._timer.stop()
        self._magnifier.hide()
        self.close()
        if self._keyboard_monitor is not None:
            NSEvent.removeMonitor_(self._keyboard_monitor)
            self._keyboard_monitor = None
        self._snapshot_image = None

    def _on_tick(self):
        pos = QCursor.pos()
        x, y = pos.x(), pos.y()
        self._magnifier.update_at(x, y, self._dpr)
        # 逻辑坐标转物理像素坐标
        px, py = int(x * self._dpr), int(y * self._dpr)
        if self._snapshot_image and self._snapshot_image.valid(px, py):
            color = self._snapshot_image.pixelColor(px, py)
            self._current_color = (color.red(), color.green(), color.blue())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.stop()
            self.color_picked.emit(*self._current_color)
        elif event.button() == Qt.RightButton:
            self.stop()
            self.pick_cancelled.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.stop()
            self.pick_cancelled.emit()

    def _on_global_key(self, event):
        if event.keyCode() == 53:
            self.stop()
            self.pick_cancelled.emit()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 30))


class ColorPreviewCard(CardWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(160, 160)
        self._color = QColor("#4A90D9")
        self._text = "#4A90D9"

    def set_color(self, hex_color):
        self._color = QColor(hex_color)
        self._text = hex_color
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._color)
        painter.drawRoundedRect(self.rect(), 12, 12)
        tc = "#000000" if is_light_color(self._color.red(), self._color.green(), self._color.blue()) else "#FFFFFF"
        painter.setPen(QColor(tc))
        painter.setFont(QFont("Helvetica", 16, QFont.Bold))
        painter.drawText(self.rect(), Qt.AlignCenter, self._text)


class HistoryColorCard(CardWidget):
    clicked = pyqtSignal(str)

    def __init__(self, hex_color, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self._hex = hex_color
        self._color = QColor(hex_color)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(hex_color)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._color)
        painter.drawRoundedRect(self.rect(), 8, 8)

    def mousePressEvent(self, event):
        self.clicked.emit(self._hex)
        super().mousePressEvent(event)


class ColorPickerWidget(PluginBase):
    plugin_id = "color_picker"
    plugin_name = "屏幕取色器"
    plugin_version = "1.0.0"
    plugin_description = "精美的屏幕取色工具，支持 HEX / RGB / HSL 格式，一键复制，历史记录"
    plugin_icon = "PALETTE"
    MAX_HISTORY = 20

    def __init__(self, parent=None):
        super().__init__(parent)
        self._picking = False
        self._current_color = (74, 144, 217)
        self._history = []
        self._overlay = PickOverlay()
        self._overlay.color_picked.connect(self._on_color_picked)
        self._overlay.pick_cancelled.connect(self._on_pick_cancelled)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(TitleLabel("🎨 屏幕取色器"))

        content = QHBoxLayout()
        content.setSpacing(20)
        self._preview = ColorPreviewCard()
        content.addWidget(self._preview)
        values = QVBoxLayout()
        values.setSpacing(12)
        values.addLayout(self._make_color_row("HEX", "hex_value", "hex_copy"))
        values.addLayout(self._make_color_row("RGB", "rgb_value", "rgb_copy"))
        values.addLayout(self._make_color_row("HSL", "hsl_value", "hsl_copy"))
        values.addStretch()
        content.addLayout(values, 1)
        layout.addLayout(content)

        hex_row = QHBoxLayout()
        hex_row.setSpacing(8)
        hex_row.addWidget(CaptionLabel("输入 HEX:"))
        self._hex_input = LineEdit()
        self._hex_input.setPlaceholderText("#FF6B35")
        self._hex_input.setFixedWidth(120)
        self._hex_input.returnPressed.connect(self._on_hex_input)
        hex_row.addWidget(self._hex_input)
        apply_btn = PushButton("应用")
        apply_btn.setFixedWidth(60)
        apply_btn.clicked.connect(self._on_hex_input)
        hex_row.addWidget(apply_btn)
        hex_row.addStretch()
        layout.addLayout(hex_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        self._pick_btn = PrimaryPushButton("🎯 开始取色")
        self._pick_btn.setFixedHeight(40)
        self._pick_btn.clicked.connect(self._start_pick)
        btn_row.addWidget(self._pick_btn, 1)
        copy_all_btn = PushButton("📋 复制全部")
        copy_all_btn.setFixedHeight(40)
        copy_all_btn.clicked.connect(self._copy_all)
        btn_row.addWidget(copy_all_btn, 1)
        layout.addLayout(btn_row)

        self._hint_label = CaptionLabel("")
        self._hint_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._hint_label)

        layout.addWidget(StrongBodyLabel("最近使用"))
        self._history_grid = QGridLayout()
        self._history_grid.setSpacing(6)
        self._history_grid.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self._history_grid)
        layout.addStretch()
        self._update_color_display(*self._current_color)

    def _make_color_row(self, label, value_attr, copy_btn_name):
        row = QHBoxLayout()
        row.setSpacing(8)
        lbl = CaptionLabel(f"{label}:")
        lbl.setFixedWidth(36)
        row.addWidget(lbl)
        value_label = CaptionLabel("")
        value_label.setStyleSheet("font-size: 14px; font-family: 'Consolas', monospace;")
        setattr(self, f"_{value_attr}", value_label)
        row.addWidget(value_label, 1)
        copy_btn = ToolButton(FluentIcon.COPY)
        copy_btn.setFixedSize(30, 30)
        copy_btn.clicked.connect(lambda checked, l=label: self._copy_format(l))
        setattr(self, f"_{copy_btn_name}", copy_btn)
        row.addWidget(copy_btn)
        return row

    def _update_color_display(self, r, g, b):
        self._current_color = (r, g, b)
        hex_str = rgb_to_hex(r, g, b)
        h, s, l = rgb_to_hsl(r, g, b)
        self._preview.set_color(hex_str)
        self._hex_value.setText(hex_str)
        self._rgb_value.setText(f"rgb({r}, {g}, {b})")
        self._hsl_value.setText(f"hsl({h}°, {s}%, {l}%)")

    def _start_pick(self):
        self._picking = True
        self._hint_label.setText("")
        self.window().hide()
        QTimer.singleShot(200, self._really_start)

    def _really_start(self):
        if not self._picking:
            return
        self._overlay.start()

    def _on_color_picked(self, r, g, b):
        self._picking = False
        self._update_color_display(r, g, b)
        self._add_to_history(r, g, b)
        self.window().show()
        InfoBar.success("取色成功", f"已选中 {rgb_to_hex(r, g, b)}",
                        parent=self, duration=2000, position=InfoBarPosition.TOP)

    def _on_pick_cancelled(self):
        self._picking = False
        self.window().show()

    def _on_hex_input(self):
        text = self._hex_input.text().strip()
        if not text:
            return
        text = text.lstrip("#")
        if len(text) == 3:
            text = text[0]*2 + text[1]*2 + text[2]*2
        if len(text) != 6:
            InfoBar.warning("格式错误", "请输入有效的 HEX 颜色值", parent=self, duration=2000)
            return
        try:
            r, g, b = int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)
            self._update_color_display(r, g, b)
            self._add_to_history(r, g, b)
        except ValueError:
            InfoBar.warning("格式错误", "请输入有效的 HEX 颜色值", parent=self, duration=2000)

    def _copy_format(self, fmt):
        r, g, b = self._current_color
        if fmt == "HEX":
            text = rgb_to_hex(r, g, b)
        elif fmt == "RGB":
            text = f"rgb({r}, {g}, {b})"
        elif fmt == "HSL":
            h, s, l = rgb_to_hsl(r, g, b)
            text = f"hsl({h}, {s}%, {l}%)"
        else:
            return
        QApplication.clipboard().setText(text)
        InfoBar.success("已复制", f"{fmt}: {text}", parent=self, duration=1500, position=InfoBarPosition.TOP)

    def _copy_all(self):
        r, g, b = self._current_color
        h, s, l = rgb_to_hsl(r, g, b)
        text = f"HEX: {rgb_to_hex(r, g, b)}\nRGB: rgb({r}, {g}, {b})\nHSL: hsl({h}, {s}%, {l}%)"
        QApplication.clipboard().setText(text)
        InfoBar.success("已复制", "全部颜色值已复制到剪贴板", parent=self, duration=1500, position=InfoBarPosition.TOP)

    def _add_to_history(self, r, g, b):
        color = (r, g, b)
        if color in self._history:
            self._history.remove(color)
        self._history.insert(0, color)
        if len(self._history) > self.MAX_HISTORY:
            self._history.pop()
        self._refresh_history()

    def _refresh_history(self):
        for i in reversed(range(self._history_grid.count())):
            item = self._history_grid.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()
        cols = 10
        for i, (r, g, b) in enumerate(self._history):
            hex_str = rgb_to_hex(r, g, b)
            card = HistoryColorCard(hex_str)
            card.clicked.connect(self._on_history_click)
            self._history_grid.addWidget(card, i // cols, i % cols)

    def _on_history_click(self, hex_str):
        color = QColor(hex_str)
        self._update_color_display(color.red(), color.green(), color.blue())

    def on_activate(self):
        super().on_activate()

    def on_deactivate(self):
        if self._picking:
            self._overlay.stop()
            self._picking = False
        super().on_deactivate()
