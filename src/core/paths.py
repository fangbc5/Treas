"""路径管理 - 统一管理应用所有数据目录

开发时：基于项目根目录
打包后（PyInstaller）：
  - 内置资源（src/plugins）→ sys._MEIPASS 临时解压目录
  - 用户数据（data/plugins/exported）→ 可执行文件同级目录
  - macOS .app → Contents/Resources/ 目录
"""

import os
import sys


def _is_frozen() -> bool:
    """是否为 PyInstaller 打包环境"""
    return getattr(sys, 'frozen', False)


def _is_macos_app() -> bool:
    """是否为 macOS .app 包"""
    return (_is_frozen()
            and sys.platform == 'darwin'
            and '.app/Contents/MacOS/' in sys.executable)


def get_app_root() -> str:
    """获取应用数据根目录（用户可读写）

    开发时：项目根目录（src 的父目录）
    macOS .app：~/Library/Application Support/Treas/
    Windows/Linux 打包：可执行文件所在目录
    """
    if _is_macos_app():
        # macOS 标准：用户数据放在 Application Support
        return os.path.join(os.path.expanduser('~'), 'Library',
                           'Application Support', 'Treas')
    elif _is_frozen():
        # Windows/Linux：可执行文件所在目录
        return os.path.dirname(sys.executable)
    # 开发时：src/core/paths.py → 向上3层到项目根目录
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_resource_root() -> str:
    """获取内置资源根目录（只读，随包分发）

    开发时：项目根目录
    打包后：sys._MEIPASS（PyInstaller 临时解压目录）
    """
    if _is_frozen():
        return sys._MEIPASS
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
    """获取内置插件目录（src/plugins，随程序打包）

    打包后从 _MEIPASS 读取（只读资源）
    """
    return os.path.join(get_resource_root(), "src", "plugins")


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


def get_plugin_data_dir() -> str:
    """获取插件专属数据目录（每个插件一个独立数据库文件）"""
    path = os.path.join(get_data_dir(), "plugin_data")
    os.makedirs(path, exist_ok=True)
    return path


def get_plugin_db_path(plugin_id: str, shared_group: str = None) -> str:
    """获取插件数据库文件路径

    Args:
        plugin_id: 插件 ID
        shared_group: 共享组名，为 None 时使用独立数据库
    Returns:
        数据库文件路径
    """
    data_dir = get_plugin_data_dir()
    if shared_group:
        return os.path.join(data_dir, f"group_{shared_group}.db")
    return os.path.join(data_dir, f"{plugin_id}.db")


def get_db_path() -> str:
    """获取数据库文件路径"""
    return os.path.join(get_data_dir(), "treas.db")


def ensure_app_dirs():
    """首次运行时确保所有必要目录存在"""
    get_data_dir()
    get_export_dir()
    get_plugins_dir()
    get_plugins_site_packages_dir()
    get_plugin_data_dir()
