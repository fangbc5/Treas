"""Treas 财务工具箱 - 应用入口"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from qfluentwidgets import setTheme, Theme, setThemeColor

from src.core.plugin_manager import PluginManager
from src.core.category_manager import CategoryManager
from src.views.main_window import MainWindow


def main():
    # 高 DPI 支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)

    # 设置默认字体
    font = QFont("Microsoft YaHei", 13)
    font.setStyleHint(QFont.SansSerif)
    app.setFont(font)

    # 设置 Fluent 主题
    setTheme(Theme.LIGHT)
    setThemeColor("#4a90d9")

    # 初始化默认分类
    cm = CategoryManager()
    cm.ensure_default_categories()

    # 发现并加载插件
    pm = PluginManager()
    pm.discover_plugins()

    # 创建主窗口
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()