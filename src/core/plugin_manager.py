"""插件管理器 - 负责插件的发现、加载、注册"""

import os
import sys
import json
import importlib
import importlib.util
from typing import Dict, Optional

from src.core.plugin_base import PluginBase
from src.core.database import Database
from src.core.dependency_manager import DependencyManager


# 首次发布时内置的插件 ID 列表（随应用分发）
BUILTIN_PLUGIN_IDS = {"calculator", "currency_converter", "simple_ledger", "social_insurance"}


class PluginManager:
    """插件管理器单例"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._plugins = {}       # plugin_id -> plugin info dict
            cls._instance._instances = {}      # plugin_id -> plugin_instance
            cls._instance._metas = {}          # plugin_id -> meta dict
            cls._instance._db = None           # Database 单例引用
            cls._instance._dm = None           # DependencyManager 单例引用
        return cls._instance

    @property
    def db(self):
        """懒加载数据库实例"""
        if self._db is None:
            self._db = Database()
        return self._db

    @property
    def dm(self) -> DependencyManager:
        """懒加载依赖管理器实例"""
        if self._dm is None:
            self._dm = DependencyManager()
        return self._dm

    @staticmethod
    def is_builtin(plugin_id: str) -> bool:
        """判断插件是否为内置插件"""
        return plugin_id in BUILTIN_PLUGIN_IDS

    def discover_plugins(self):
        """扫描内置插件和自定义插件目录，发现所有可用插件"""
        from src.core.paths import get_builtin_plugins_dir, get_plugins_dir

        # 先扫描内置插件目录（src/plugins）
        builtin_dir = get_builtin_plugins_dir()
        if os.path.isdir(builtin_dir):
            self._scan_plugin_dir(builtin_dir)

        # 再扫描自定义插件目录（plugins）
        custom_dir = get_plugins_dir()
        if os.path.isdir(custom_dir):
            self._scan_plugin_dir(custom_dir)

    def _scan_plugin_dir(self, plugins_dir: str):
        """扫描指定目录下的插件"""
        for item in os.listdir(plugins_dir):
            plugin_dir = os.path.join(plugins_dir, item)
            manifest_path = os.path.join(plugin_dir, "plugin.json")

            if not os.path.isdir(plugin_dir) or not os.path.exists(manifest_path):
                continue

            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)

                plugin_id = meta.get("id")
                if not plugin_id:
                    continue

                # 如果已注册（内置插件优先），跳过重复
                if plugin_id in self._plugins:
                    continue

                self._metas[plugin_id] = meta
                # 延迟加载：先不实例化，只记录元信息
                self._plugins[plugin_id] = {
                    "meta": meta,
                    "dir": plugin_dir,
                    "loaded": False,
                }
                # 自动注册到数据库（使用 plugin.json 的默认分类）
                self.ensure_registered(plugin_id)
                # 保存依赖声明到数据库（来自 plugin.json 的 dependencies 字段）
                dependencies = meta.get("dependencies", [])
                if dependencies:
                    self.dm.save_dependencies(plugin_id, dependencies)
            except Exception as e:
                print(f"[PluginManager] 加载插件清单失败 {item}: {e}")

    def load_plugin(self, plugin_id: str) -> Optional[PluginBase]:
        """加载并实例化指定插件"""
        # 如果已有实例，直接返回
        if plugin_id in self._instances:
            return self._instances[plugin_id]

        if plugin_id not in self._plugins:
            return None

        plugin_info = self._plugins[plugin_id]
        meta = plugin_info["meta"]
        plugin_dir = plugin_info["dir"]

        entry_file = meta.get("entry", "widget.py")
        entry_class = meta.get("entry_class", "PluginWidget")

        entry_path = os.path.join(plugin_dir, entry_file)
        if not os.path.exists(entry_path):
            print(f"[PluginManager] 入口文件不存在: {entry_path}")
            return None

        try:
            # 确保插件共享依赖目录在 sys.path 中
            self.dm.ensure_site_packages_in_path()
            # 动态导入插件模块
            module_name = f"src.plugins.{plugin_id}.{os.path.splitext(entry_file)[0]}"
            spec = importlib.util.spec_from_file_location(module_name, entry_path)
            module = importlib.util.module_from_spec(spec)
            # 注册到 sys.modules，使 _get_plugin_dir() 能正确定位插件目录
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # 获取插件类并实例化
            plugin_class = getattr(module, entry_class, None)
            if plugin_class is None:
                print(f"[PluginManager] 未找到类 {entry_class} 在 {entry_file}")
                return None

            instance = plugin_class()
            if not isinstance(instance, PluginBase):
                print(f"[PluginManager] {entry_class} 未继承 PluginBase")
                return None

            # 注入数据库配置（仅自定义插件，不影响内置插件）
            db_config = meta.get("database")
            if db_config and not self.is_builtin(plugin_id):
                instance._db_config = db_config
                # 首次加载时初始化数据库
                try:
                    instance.init_database()
                except Exception as e:
                    print(f"[PluginManager] 初始化插件 {plugin_id} 数据库失败: {e}")

            plugin_info["loaded"] = True
            self._instances[plugin_id] = instance
            return instance

        except Exception as e:
            print(f"[PluginManager] 加载插件 {plugin_id} 失败: {e}")
            return None

    def unload_plugin(self, plugin_id: str):
        """卸载插件"""
        if plugin_id in self._instances:
            instance = self._instances[plugin_id]
            instance.on_deactivate()
            instance.deleteLater()
            del self._instances[plugin_id]

        if plugin_id in self._plugins:
            self._plugins[plugin_id]["loaded"] = False

    def get_plugin(self, plugin_id: str) -> Optional[PluginBase]:
        """获取插件实例（如未加载则先加载）"""
        if plugin_id in self._instances:
            return self._instances[plugin_id]
        return self.load_plugin(plugin_id)

    def _get_hidden_plugin_ids(self) -> set:
        """获取所有被隐藏的插件 ID 集合"""
        rows = self.db.query("SELECT plugin_id FROM hidden_tools")
        return {row["plugin_id"] for row in rows}

    def list_plugins(self, include_hidden: bool = False) -> list:
        """列出所有已发现的插件元信息（排除已隐藏的，内置工具置顶）"""
        hidden_ids = self._get_hidden_plugin_ids() if not include_hidden else set()
        result = []
        for plugin_id, info in self._plugins.items():
            # 跳过已隐藏的工具
            if not include_hidden and plugin_id in hidden_ids:
                continue
            meta = dict(info["meta"])
            meta["loaded"] = info["loaded"]
            meta["plugin_id"] = plugin_id
            meta["is_builtin"] = self.is_builtin(plugin_id)
            # 从数据库获取实际分类
            meta["_db_category"] = self.get_plugin_category_name(plugin_id)
            # 依赖状态摘要
            meta["_dep_summary"] = self.dm.get_dependency_summary(plugin_id)
            result.append(meta)
        # 内置工具置顶排序（按固定顺序，再按名称）
        _builtin_order = {pid: i for i, pid in enumerate(BUILTIN_PLUGIN_IDS)}
        result.sort(key=lambda p: (
            0 if p["is_builtin"] else 1,
            _builtin_order.get(p["plugin_id"], 999),
            p.get("name", ""),
        ))
        return result

    def get_plugin_meta(self, plugin_id: str) -> Optional[dict]:
        """获取单个插件的元信息"""
        return self._metas.get(plugin_id)

    def _resolve_category_id(self, category_name: str) -> Optional[int]:
        """根据分类名称查找 category_id"""
        if not category_name:
            return None
        cat = self.db.query_one(
            "SELECT id FROM categories WHERE name = ?", (category_name,)
        )
        return cat["id"] if cat else None

    def ensure_registered(self, plugin_id: str, category_name: str = None):
        """确保插件在 plugin_registry 中注册
        
        首次注册时：使用 category_name 或 plugin.json 中的默认 category
        已注册时：不做任何修改（尊重用户的分类操作）
        """
        existing = self.db.query_one(
            "SELECT id FROM plugin_registry WHERE plugin_id = ?",
            (plugin_id,),
        )

        if existing:
            return

        # 确定分类（仅首次注册时使用）
        if category_name is None:
            meta = self._metas.get(plugin_id, {})
            category_name = meta.get("category", None)
        category_id = self._resolve_category_id(category_name)

        self.db.execute(
            "INSERT INTO plugin_registry (plugin_id, category_id) VALUES (?, ?)",
            (plugin_id, category_id),
        )

    def set_plugin_category(self, plugin_id: str, category_name: str = None):
        """设置插件的分类（category_name=None 表示无分类）"""
        category_id = self._resolve_category_id(category_name)

        existing = self.db.query_one(
            "SELECT id FROM plugin_registry WHERE plugin_id = ?", (plugin_id,)
        )
        if existing:
            self.db.execute(
                "UPDATE plugin_registry SET category_id = ? WHERE plugin_id = ?",
                (category_id, plugin_id),
            )
        else:
            self.db.execute(
                "INSERT INTO plugin_registry (plugin_id, category_id) VALUES (?, ?)",
                (plugin_id, category_id),
            )

    def get_plugin_category_name(self, plugin_id: str) -> Optional[str]:
        """获取插件的分类名称（从数据库），返回 None 表示未分类"""
        row = self.db.query_one(
            "SELECT category_id FROM plugin_registry WHERE plugin_id = ?",
            (plugin_id,),
        )
        if row and row["category_id"]:
            cat = self.db.query_one(
                "SELECT name FROM categories WHERE id = ?", (row["category_id"],)
            )
            if cat:
                return cat["name"]
        return None

    def get_plugins_by_category(self, category_name: str = None) -> list:
        """按分类筛选插件（排除已隐藏的，内置工具置顶）"""
        all_plugins = self.list_plugins()
        if category_name is None or category_name == "全部工具":
            return all_plugins
        return [p for p in all_plugins if p.get("_db_category") == category_name]

    def delete_plugin(self, plugin_id: str, keep_data: bool = True) -> bool:
        """删除插件

        内置插件：软删除（标记为隐藏）
        自定义插件：隐藏 + 可选删除插件文件和数据

        Args:
            plugin_id: 插件 ID
            keep_data: 是否保留插件数据（仅自定义插件有效）

        Returns:
            True 表示成功
        """
        if plugin_id not in self._plugins:
            return False

        # 先卸载实例
        self.unload_plugin(plugin_id)

        # 标记为隐藏
        existing = self.db.query_one(
            "SELECT id FROM hidden_tools WHERE plugin_id = ?", (plugin_id,)
        )
        if not existing:
            is_builtin = 1 if self.is_builtin(plugin_id) else 0
            self.db.execute(
                "INSERT INTO hidden_tools (plugin_id, is_builtin) VALUES (?, ?)",
                (plugin_id, is_builtin),
            )

        # 自定义插件：删除插件文件
        if not self.is_builtin(plugin_id):
            self._delete_plugin_files(plugin_id, keep_data)

        return True

    def _delete_plugin_files(self, plugin_id: str, keep_data: bool = True):
        """删除自定义插件的文件

        Args:
            plugin_id: 插件 ID
            keep_data: 是否保留数据库文件
        """
        import shutil

        plugin_info = self._plugins.get(plugin_id)
        if not plugin_info:
            return

        # 删除插件目录
        plugin_dir = plugin_info.get("dir")
        if plugin_dir and os.path.isdir(plugin_dir):
            try:
                shutil.rmtree(plugin_dir)
            except Exception as e:
                print(f"[PluginManager] 删除插件目录失败 {plugin_dir}: {e}")

        # 删除数据库文件（如果不保留）
        if not keep_data:
            meta = plugin_info.get("meta", {})
            db_config = meta.get("database")
            if db_config:
                from src.core.paths import get_plugin_db_path

                db_path = get_plugin_db_path(plugin_id, db_config.get("shared_group"))
                if os.path.exists(db_path):
                    try:
                        os.remove(db_path)
                    except Exception as e:
                        print(f"[PluginManager] 删除数据库文件失败 {db_path}: {e}")

        # 从内存中移除
        if plugin_id in self._plugins:
            del self._plugins[plugin_id]
        if plugin_id in self._metas:
            del self._metas[plugin_id]

    def get_plugin_db_info(self, plugin_id: str) -> dict:
        """获取插件的数据库信息（用于删除确认对话框）

        Returns:
            {"has_db": bool, "db_path": str, "db_exists": bool, "db_size": int}
        """
        meta = self._metas.get(plugin_id, {})
        db_config = meta.get("database")
        if not db_config:
            return {"has_db": False, "db_path": None, "db_exists": False, "db_size": 0}

        from src.core.paths import get_plugin_db_path
        import os

        db_path = get_plugin_db_path(plugin_id, db_config.get("shared_group"))
        exists = os.path.exists(db_path)
        size = os.path.getsize(db_path) if exists else 0

        return {
            "has_db": True,
            "db_path": db_path,
            "db_exists": exists,
            "db_size": size,
        }

    def reset_builtin_plugins(self) -> int:
        """重置所有内置插件（取消隐藏）
        返回恢复的插件数量
        """
        hidden_builtins = self.db.query(
            "SELECT plugin_id FROM hidden_tools WHERE is_builtin = 1"
        )
        count = len(hidden_builtins)
        if count > 0:
            self.db.execute("DELETE FROM hidden_tools WHERE is_builtin = 1")
        # 重新发现插件（确保内置插件都被加载）
        self.discover_plugins()
        return count
