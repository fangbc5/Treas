"""数据库管理模块 - SQLite 本地存储"""

import sqlite3
import sys
import os
from datetime import datetime


class Database:
    """数据库单例管理器"""

    _instance = None

    def __new__(cls, db_path=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def _get_data_dir(self):
        """获取跨平台应用数据目录"""
        app_name = "Treas"
        if sys.platform == "darwin":
            base = os.path.expanduser("~/Library/Application Support")
        elif sys.platform == "win32":
            base = os.environ.get(
                "LOCALAPPDATA",
                os.path.expanduser("~/AppData/Local")
            )
        else:  # Linux 及其他
            base = os.environ.get(
                "XDG_DATA_HOME",
                os.path.expanduser("~/.local/share")
            )
        data_dir = os.path.join(base, app_name)
        os.makedirs(data_dir, exist_ok=True)
        return data_dir

    def __init__(self, db_path=None):
        if self._initialized:
            return
        if db_path is None:
            data_dir = self._get_data_dir()
            db_path = os.path.join(data_dir, "treas.db")
        self.db_path = db_path
        self._initialized = True
        self._init_tables()

    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_tables(self):
        """初始化数据表"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            # 分类表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    icon TEXT DEFAULT '📁',
                    sort_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 插件注册表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS plugin_registry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plugin_id TEXT NOT NULL UNIQUE,
                    category_id INTEGER,
                    is_enabled BOOLEAN DEFAULT 1,
                    installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
                )
            """)

            conn.commit()
        finally:
            conn.close()

    def execute(self, sql, params=None):
        """执行写操作"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            conn.commit()
            return cursor
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def query(self, sql, params=None):
        """执行查询操作，返回字典列表"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def query_one(self, sql, params=None):
        """查询单条记录"""
        results = self.query(sql, params)
        return results[0] if results else None