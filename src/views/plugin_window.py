"""插件运行窗口 - 基于 Fluent 组件"""

from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QScrollArea
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from qfluentwidgets import FluentIcon

from src.utils.icons import fluent_icon_from_name
from src.core.plugin_manager import PluginManager


class PluginWindow(QMainWindow):
    """插件独立运行窗口"""

    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self._init_ui()

    def _init_ui(self):
        # 从 PluginManager 获取完整的 plugin.json 元数据
        pm = PluginManager()
        meta = pm.get_plugin_meta(self.plugin.plugin_id) or self.plugin.get_meta()
        icon_name = meta.get("icon", "APPLICATION")
        icon = fluent_icon_from_name(icon_name)
        self.setWindowIcon(icon.icon())
        self.setWindowTitle(meta.get("name", "工具"))

        # 支持 plugin.json 中的 window_size 自定义窗口大小
        win_size = meta.get("window_size", None)
        if win_size and len(win_size) == 2:
            w, h = win_size
            self.setMinimumSize(w, h)
            self.resize(w, h)
        else:
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

        # 小窗口直接嵌入，大窗口用滚动区域包裹
        if win_size and len(win_size) == 2 and win_size[0] <= 400:
            layout.addWidget(widget)
        else:
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