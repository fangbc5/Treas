"""插件管理器 - 负责插件的发现、加载、注册"""

import os
import json
import shutil
import importlib
import importlib.util
from typing import Dict, Optional

from src.core.plugin_base import PluginBase
from src.core.database import Database


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
        return cls._instance

    @property
    def db(self):
        """懒加载数据库实例"""
        if self._db is None:
            self._db = Database()
        return self._db

    @staticmethod
    def is_builtin(plugin_id: str) -> bool:
        """判断插件是否为内置插件"""
        return plugin_id in BUILTIN_PLUGIN_IDS

    def discover_plugins(self):
        """扫描 plugins/ 目录，发现所有可用插件"""
        from src.core.paths import get_plugins_dir
        plugins_dir = get_plugins_dir()

        if not os.path.isdir(plugins_dir):
            return

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

                self._metas[plugin_id] = meta
                # 延迟加载：先不实例化，只记录元信息
                self._plugins[plugin_id] = {
                    "meta": meta,
                    "dir": plugin_dir,
                    "loaded": False,
                }
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
            # 动态导入插件模块
            module_name = f"src.plugins.{plugin_id}.{os.path.splitext(entry_file)[0]}"
            spec = importlib.util.spec_from_file_location(module_name, entry_path)
            module = importlib.util.module_from_spec(spec)
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

    def get_plugins_by_category(self, category_name: str = None) -> list:
        """按分类筛选插件（排除已隐藏的，内置工具置顶）"""
        all_plugins = self.list_plugins()
        if category_name is None or category_name == "全部工具":
            return all_plugins
        return [p for p in all_plugins if p.get("category") == category_name]

    def delete_plugin(self, plugin_id: str) -> bool:
        """删除插件
        - 内置插件：标记为隐藏（从列表中移除，文件保留）
        - 自定义插件：彻底删除文件
        返回 True 表示成功
        """
        if plugin_id not in self._plugins:
            return False

        # 先卸载实例
        self.unload_plugin(plugin_id)

        if self.is_builtin(plugin_id):
            # 内置插件：仅标记隐藏
            existing = self.db.query_one(
                "SELECT id FROM hidden_tools WHERE plugin_id = ?", (plugin_id,)
            )
            if not existing:
                self.db.execute(
                    "INSERT INTO hidden_tools (plugin_id, is_builtin) VALUES (?, 1)",
                    (plugin_id,),
                )
        else:
            # 自定义插件：删除文件并从内存移除
            plugin_dir = self._plugins[plugin_id]["dir"]
            if os.path.isdir(plugin_dir):
                shutil.rmtree(plugin_dir)
            if plugin_id in self._plugins:
                del self._plugins[plugin_id]
            if plugin_id in self._metas:
                del self._metas[plugin_id]

        return True

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
