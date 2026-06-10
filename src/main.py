"""Treas 淼淼百宝箱 - 应用入口"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# PyInstaller 打包后 darkdetect 版本检测修复
# 必须在 qfluentwidgets 导入之前设置
if getattr(sys, 'frozen', False) and sys.platform == 'darwin':
    os.environ['SYSTEM_VERSION_COMPAT'] = '0'

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt

from qfluentwidgets import setTheme, Theme, setThemeColor

from src.core.plugin_manager import PluginManager
from src.core.category_manager import CategoryManager
from src.views.main_window import MainWindow


def main():
    # Windows 任务栏图标：必须在 QApplication 创建之前设置 AppUserModelID
    if sys.platform == 'win32':
        import ctypes
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('com.treas.app')
        except Exception:
            pass

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

    # 确保应用数据目录存在（首次运行时创建）
    from src.core.paths import ensure_app_dirs
    ensure_app_dirs()

    # 初始化默认分类
    cm = CategoryManager()
    cm.ensure_default_categories()

    # 发现并加载插件
    pm = PluginManager()
    pm.discover_plugins()

    # 设置应用图标（Windows 使用 ICO 含多尺寸，其他平台使用 PNG）
    if sys.platform == 'win32':
        icon_name = 'icon.ico'
    else:
        icon_name = 'icon_1024.png'
    if getattr(sys, 'frozen', False):
        icon_path = os.path.join(sys._MEIPASS, 'resources', icon_name)
    else:
        icon_path = os.path.join(project_root, 'resources', icon_name)
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # 创建主窗口
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()