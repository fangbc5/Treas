"""插件管理器 - 负责插件的发现、加载、注册"""

import os
import json
import importlib
import importlib.util
from typing import Dict, Optional

from src.core.plugin_base import PluginBase


class PluginManager:
    """插件管理器单例"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._plugins = {}       # plugin_id -> plugin_class
            cls._instance._instances = {}      # plugin_id -> plugin_instance
            cls._instance._metas = {}          # plugin_id -> meta dict
        return cls._instance

    def discover_plugins(self):
        """扫描 plugins/ 目录，发现所有可用插件"""
        plugins_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "plugins"
        )

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

    def list_plugins(self) -> list:
        """列出所有已发现的插件元信息"""
        result = []
        for plugin_id, info in self._plugins.items():
            meta = dict(info["meta"])
            meta["loaded"] = info["loaded"]
            meta["plugin_id"] = plugin_id
            result.append(meta)
        return result

    def get_plugin_meta(self, plugin_id: str) -> Optional[dict]:
        """获取单个插件的元信息"""
        return self._metas.get(plugin_id)

    def get_plugins_by_category(self, category_name: str = None) -> list:
        """按分类筛选插件"""
        all_plugins = self.list_plugins()
        if category_name is None or category_name == "全部工具":
            return all_plugins
        return [p for p in all_plugins if p.get("category") == category_name]