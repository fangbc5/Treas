"""插件运行窗口 - 基于 Fluent 组件"""

from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget
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
        self.setMinimumSize(500, 400)
        self.resize(600, 500)

        # 中央容器
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # 激活插件并获取组件
        self.plugin.on_activate()
        widget = self.plugin.get_widget()
        widget.setParent(central)
        layout.addWidget(widget)

    def closeEvent(self, event):
        """窗口关闭时停用插件"""
        self.plugin.on_deactivate()
        self.plugin.setParent(None)
        super().closeEvent(event)