"""插件运行窗口 - 基于 Fluent 组件"""

from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QScrollArea
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from qfluentwidgets import FluentIcon

from src.utils.icons import fluent_icon_from_name


class PluginWindow(QMainWindow):
    """插件独立运行窗口"""

    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self._init_ui()

    def _init_ui(self):
        meta = self.plugin.get_meta()
        icon_name = meta.get("icon", "APPLICATION")
        icon = fluent_icon_from_name(icon_name)
        self.setWindowIcon(icon.icon())
        self.setWindowTitle(meta.get("name", "工具"))
        self.setMinimumSize(600, 500)
        self.resize(700, 700)

        # 中央容器
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # 激活插件并获取组件
        self.plugin.on_activate()
        widget = self.plugin.get_widget()
        widget.setParent(central)

        # 用滚动区域包裹，防止内容超出窗口
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(widget)
        layout.addWidget(scroll)

    def closeEvent(self, event):
        """窗口关闭时停用插件"""
        self.plugin.on_deactivate()
        self.plugin.setParent(None)
        super().closeEvent(event)