"""插件基类 - 所有工具插件必须继承此类"""

import sqlite3
from PyQt5.QtWidgets import QWidget


class PluginBase(QWidget):
    """插件基类，定义统一接口

    数据库支持（仅自定义插件）：
    - plugin.json 中声明 "database": {"shared_group": null, "init_sql": "init.sql", "version": 1}
    - 插件内通过 self.get_db() 获取专属数据库连接
    - 可覆盖 init_database() 自定义初始化逻辑
    - 可覆盖 on_db_upgrade(old_ver, new_ver) 处理数据库版本迁移
    """

    # 子类必须覆盖以下属性
    plugin_id = ""
    plugin_name = ""
    plugin_version = "1.0.0"
    plugin_description = ""
    plugin_icon = "🔧"

    # 数据库配置（由 PluginManager 加载 plugin.json 后注入）
    _db_config = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active = False

    def get_widget(self) -> QWidget:
        """返回插件的UI组件"""
        return self

    def on_activate(self):
        """插件被激活时调用"""
        self._active = True

    def on_deactivate(self):
        """插件被关闭/隐藏时调用"""
        self._active = False

    @property
    def is_active(self) -> bool:
        return self._active

    def get_meta(self) -> dict:
        """获取插件元信息"""
        return {
            "id": self.plugin_id,
            "name": self.plugin_name,
            "version": self.plugin_version,
            "description": self.plugin_description,
            "icon": self.plugin_icon,
        }

    # ========== 数据库支持（自定义插件专用） ==========

    def get_db(self) -> sqlite3.Connection:
        """获取插件专属数据库连接

        仅自定义插件可用（plugin.json 中声明了 database 配置）。
        内置插件应使用公共 Database 单例。

        Returns:
            sqlite3.Connection: 已开启 row_factory 和 foreign_keys 的数据库连接

        Raises:
            RuntimeError: 插件未配置数据库或 plugin_id 为空
        """
        if not self.plugin_id:
            raise RuntimeError("plugin_id 未设置，无法获取数据库")
        if not self._db_config:
            raise RuntimeError(
                f"插件 {self.plugin_id} 未配置数据库，"
                "请在 plugin.json 中添加 database 配置"
            )

        from src.core.paths import get_plugin_db_path

        shared_group = self._db_config.get("shared_group")
        db_path = get_plugin_db_path(self.plugin_id, shared_group)

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def get_db_path(self) -> str:
        """获取插件数据库文件路径

        Returns:
            str: 数据库文件的绝对路径
        """
        from src.core.paths import get_plugin_db_path

        shared_group = self._db_config.get("shared_group") if self._db_config else None
        return get_plugin_db_path(self.plugin_id, shared_group)

    def init_database(self):
        """初始化插件数据库

        默认行为：
        1. 如果 plugin.json 中指定了 init_sql，读取并执行 SQL 文件
        2. 如果指定了 version，记录到 _plugin_db_meta 表

        子类可覆盖此方法实现自定义初始化逻辑。
        """
        if not self._db_config:
            return

        conn = self.get_db()
        try:
            # 创建元信息表（跟踪数据库版本）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS _plugin_db_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            # 执行 init_sql 文件
            init_sql = self._db_config.get("init_sql")
            if init_sql:
                import os

                # 从插件目录查找 SQL 文件
                plugin_dir = self._get_plugin_dir()
                sql_path = os.path.join(plugin_dir, init_sql)
                if os.path.exists(sql_path):
                    with open(sql_path, "r", encoding="utf-8") as f:
                        sql_content = f.read()
                    if sql_content.strip():
                        conn.executescript(sql_content)

            # 记录/更新数据库版本
            version = self._db_config.get("version", 1)
            conn.execute(
                "INSERT OR REPLACE INTO _plugin_db_meta (key, value) VALUES (?, ?)",
                ("db_version", str(version)),
            )
            conn.commit()
        finally:
            conn.close()

    def on_db_upgrade(self, old_version: int, new_version: int):
        """数据库版本升级回调

        当 plugin.json 中的 version 大于已记录的版本时调用。
        子类可覆盖此方法实现迁移逻辑。

        Args:
            old_version: 旧版本号
            new_version: 新版本号
        """
        pass

    def _get_plugin_dir(self) -> str:
        """获取插件所在目录"""
        import os
        import sys

        module_name = type(self).__module__
        if module_name in sys.modules and hasattr(sys.modules[module_name], '__file__'):
            return os.path.dirname(os.path.abspath(sys.modules[module_name].__file__))
        # fallback: 当前工作目录
        return os.getcwd()
