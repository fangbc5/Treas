"""屏幕截图 - 区域选择截图工具"""

import sys
import os
from datetime import datetime

_project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QApplication, QLabel, QWidget,
    QFileDialog,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QRect
from PyQt5.QtGui import QColor, QPixmap, QPainter, QPen, QFont, QImage, QGuiApplication

from qfluentwidgets import (
    PushButton, PrimaryPushButton, CaptionLabel, TitleLabel,
    FluentIcon, InfoBar, InfoBarPosition, CardWidget,
)

from src.core.plugin_base import PluginBase
from AppKit import NSEvent, NSKeyDownMask


class CaptureOverlay(QWidget):
    """全屏遮罩 - 拖拽选择截图区域"""
    area_selected = pyqtSignal(int, int, int, int)  # x, y, w, h (逻辑坐标)
    capture_cancelled = pyqtSignal()

    def __init__(self):
        super().__init__(None, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._snapshot = None
        self._dpr = 1.0
        self._start_pos = None
        self._current_pos = None
        self._dragging = False
        self._keyboard_monitor = None

    def start(self, snapshot: QPixmap, dpr: float):
        self._snapshot = snapshot
        self._dpr = dpr
        screen = QApplication.primaryScreen()
        geo = screen.geometry()
        self.setGeometry(geo)
        self._start_pos = None
        self._current_pos = None
        self._dragging = False
        self.showNormal()
        self.raise_()
        self.activateWindow()
        # 注册全局 ESC
        self._keyboard_monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
            NSKeyDownMask, self._on_global_key
        )

    def stop(self):
        self.close()
        if self._keyboard_monitor is not None:
            NSEvent.removeMonitor_(self._keyboard_monitor)
            self._keyboard_monitor = None
        self._snapshot = None

    def _on_global_key(self, event):
        if event.keyCode() == 53:  # ESC
            self.stop()
            self.capture_cancelled.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.stop()
            self.capture_cancelled.emit()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._start_pos = event.pos()
            self._current_pos = event.pos()
            self._dragging = True
            self.update()
        elif event.button() == Qt.RightButton:
            self.stop()
            self.capture_cancelled.emit()

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._current_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            self._current_pos = event.pos()
            if self._start_pos and self._current_pos:
                x1 = min(self._start_pos.x(), self._current_pos.x())
                y1 = min(self._start_pos.y(), self._current_pos.y())
                x2 = max(self._start_pos.x(), self._current_pos.x())
                y2 = max(self._start_pos.y(), self._current_pos.y())
                w = x2 - x1
                h = y2 - y1
                if w > 5 and h > 5:
                    self.stop()
                    self.area_selected.emit(x1, y1, w, h)
                    return
            self.update()

    def _get_selection(self):
        if not self._start_pos or not self._current_pos:
            return None
        x1 = min(self._start_pos.x(), self._current_pos.x())
        y1 = min(self._start_pos.y(), self._current_pos.y())
        x2 = max(self._start_pos.x(), self._current_pos.x())
        y2 = max(self._start_pos.y(), self._current_pos.y())
        return QRect(x1, y1, x2 - x1, y2 - y1)

    def paintEvent(self, event):
        if not self._snapshot:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # 画截图
        painter.drawPixmap(0, 0, self._snapshot)
        sel = self._get_selection()
        if sel and sel.width() > 0 and sel.height() > 0:
            # 选区外半透明遮罩
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, 120))
            # 上
            painter.drawRect(0, 0, self.width(), sel.top())
            # 下
            painter.drawRect(0, sel.bottom(), self.width(), self.height() - sel.bottom())
            # 左
            painter.drawRect(0, sel.top(), sel.left(), sel.height())
            # 右
            painter.drawRect(sel.right(), sel.top(), self.width() - sel.right(), sel.height())
            # 选区边框
            painter.setPen(QPen(QColor(0, 168, 243), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(sel)
            # 尺寸信息
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Helvetica", 12))
            text = f"{sel.width()} × {sel.height()}"
            tx = sel.x() + (sel.width() - painter.fontMetrics().horizontalAdvance(text)) // 2
            ty = sel.y() - 8 if sel.y() > 30 else sel.bottom() + 20
            # 背景
            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(text) + 12
            th = fm.height() + 6
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, 180))
            painter.drawRoundedRect(tx - 6, ty - th + 4, tw, th, 4, 4)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(tx, ty, text)
        else:
            # 全屏半透明遮罩
            painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
            # 提示文字
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Helvetica", 24))
            painter.drawText(self.rect(), Qt.AlignCenter, "拖拽选择截图区域\n右键或 ESC 取消")


class ScreenCaptureWidget(PluginBase):
    """屏幕截图插件"""

    plugin_id = "screen_capture"
    plugin_name = "屏幕截图"
    plugin_version = "1.0.0"
    plugin_description = "精美的屏幕截图工具，支持区域选择、复制到剪贴板、保存到文件"
    plugin_icon = "PHOTO"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._capturing = False
        self._snapshot = None
        self._dpr = 1.0
        self._overlay = CaptureOverlay()
        self._overlay.area_selected.connect(self._on_area_selected)
        self._overlay.capture_cancelled.connect(self._on_capture_cancelled)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(TitleLabel("📸 屏幕截图"))

        # 按钮
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        self._capture_btn = PrimaryPushButton("🎯 开始截图")
        self._capture_btn.setFixedHeight(40)
        self._capture_btn.clicked.connect(self._start_capture)
        btn_row.addWidget(self._capture_btn, 1)
        self._copy_btn = PushButton("📋 复制到剪贴板")
        self._copy_btn.setFixedHeight(40)
        self._copy_btn.setEnabled(False)
        self._copy_btn.clicked.connect(self._copy_to_clipboard)
        btn_row.addWidget(self._copy_btn, 1)
        self._save_btn = PushButton("💾 保存到文件")
        self._save_btn.setFixedHeight(40)
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._save_to_file)
        btn_row.addWidget(self._save_btn, 1)
        layout.addLayout(btn_row)

        # 预览区域
        self._preview_label = QLabel("截图将显示在这里")
        self._preview_label.setAlignment(Qt.AlignCenter)
        self._preview_label.setMinimumHeight(300)
        self._preview_label.setStyleSheet(
            "background-color: #2b2b2b; border-radius: 8px; color: #888; font-size: 16px;"
        )
        layout.addWidget(self._preview_label, 1)

        # 信息栏
        self._info_label = CaptionLabel("")
        self._info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._info_label)

        # 底部按钮
        bottom_row = QHBoxLayout()
        self._clear_btn = PushButton("🗑️ 清除截图")
        self._clear_btn.setFixedHeight(36)
        self._clear_btn.setEnabled(False)
        self._clear_btn.clicked.connect(self._clear_capture)
        bottom_row.addWidget(self._clear_btn)
        bottom_row.addStretch()
        layout.addLayout(bottom_row)

    def _start_capture(self):
        self._capturing = True
        self.window().hide()
        QTimer.singleShot(200, self._really_start)

    def _really_start(self):
        if not self._capturing:
            return
        screen = QApplication.primaryScreen()
        geo = screen.geometry()
        self._dpr = screen.devicePixelRatio()
        self._snapshot = screen.grabWindow(0, geo.x(), geo.y(), geo.width(), geo.height())
        self._overlay.start(self._snapshot, self._dpr)

    def _on_area_selected(self, x, y, w, h):
        """选区确认 - 裁剪截图"""
        self._capturing = False
        # 逻辑坐标转物理像素
        px = int(x * self._dpr)
        py = int(y * self._dpr)
        pw = int(w * self._dpr)
        ph = int(h * self._dpr)
        self._cropped = self._snapshot.copy(px, py, pw, ph)
        self._cropped.setDevicePixelRatio(self._dpr)
        # 显示预览
        preview = self._cropped.scaled(
            self._preview_label.width(), self._preview_label.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self._preview_label.setPixmap(preview)
        self._preview_label.setStyleSheet("background-color: #2b2b2b; border-radius: 8px;")
        self._info_label.setText(f"截图尺寸: {w} × {h} px")
        # 启用按钮
        self._copy_btn.setEnabled(True)
        self._save_btn.setEnabled(True)
        self._clear_btn.setEnabled(True)
        self.window().show()
        InfoBar.success("截图成功", f"已截取 {w}×{h} 区域",
                        parent=self, duration=2000, position=InfoBarPosition.TOP)

    def _on_capture_cancelled(self):
        self._capturing = False
        self.window().show()

    def _copy_to_clipboard(self):
        if hasattr(self, '_cropped') and self._cropped:
            QApplication.clipboard().setPixmap(self._cropped)
            InfoBar.success("已复制", "截图已复制到剪贴板",
                            parent=self, duration=1500, position=InfoBarPosition.TOP)

    def _save_to_file(self):
        if not hasattr(self, '_cropped') or not self._cropped:
            return
        default_name = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path, _ = QFileDialog.getSaveFileName(
            self, "保存截图", default_name,
            "PNG 图片 (*.png);;JPEG 图片 (*.jpg);;BMP 图片 (*.bmp)"
        )
        if path:
            # 保存时去掉 DPR，保存原始像素
            save_img = self._cropped.toImage()
            save_img.setDevicePixelRatio(1.0)
            save_pix = QPixmap.fromImage(save_img)
            save_pix.save(path)
            InfoBar.success("已保存", f"截图已保存到 {path}",
                            parent=self, duration=2000, position=InfoBarPosition.TOP)

    def _clear_capture(self):
        self._cropped = None
        self._snapshot = None
        self._preview_label.clear()
        self._preview_label.setText("截图将显示在这里")
        self._preview_label.setStyleSheet(
            "background-color: #2b2b2b; border-radius: 8px; color: #888; font-size: 16px;"
        )
        self._info_label.setText("")
        self._copy_btn.setEnabled(False)
        self._save_btn.setEnabled(False)
        self._clear_btn.setEnabled(False)

    def on_deactivate(self):
        if self._capturing:
            self._overlay.stop()
            self._capturing = False
        super().on_deactivate()
