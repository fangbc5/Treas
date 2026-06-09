"""路径管理 - 统一管理应用所有数据目录

开发时：基于项目根目录
打包后：基于可执行文件所在目录
"""

import os
import sys


def get_app_root() -> str:
    """获取应用根目录

    开发时：项目根目录（src 的父目录）
    打包后（PyInstaller）：可执行文件所在目录
    """
    # PyInstaller 打包后会有 _MEIPASS 属性
    if getattr(sys, 'frozen', False):
        # 打包后：可执行文件所在目录
        return os.path.dirname(sys.executable)
    # 开发时：src/core/paths.py → 向上3层到项目根目录
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_data_dir() -> str:
    """获取数据目录（数据库等）"""
    path = os.path.join(get_app_root(), "data")
    os.makedirs(path, exist_ok=True)
    return path


def get_export_dir() -> str:
    """获取导出目录"""
    path = os.path.join(get_app_root(), "exported")
    os.makedirs(path, exist_ok=True)
    return path


def get_builtin_plugins_dir() -> str:
    """获取内置插件目录（src/plugins，随程序打包）"""
    return os.path.join(get_app_root(), "src", "plugins")


def get_plugins_dir() -> str:
    """获取用户自定义插件目录"""
    path = os.path.join(get_app_root(), "plugins")
    os.makedirs(path, exist_ok=True)
    return path


def get_plugins_site_packages_dir() -> str:
    """获取插件共享第三方依赖目录"""
    path = os.path.join(get_app_root(), "plugins", ".site-packages")
    os.makedirs(path, exist_ok=True)
    return path


def get_db_path() -> str:
    """获取数据库文件路径"""
    return os.path.join(get_data_dir(), "treas.db")
