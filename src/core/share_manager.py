"""分享管理器 - 插件的导入/导出"""

import os
import shutil
import zipfile
from src.core.plugin_manager import PluginManager
from src.core.paths import get_export_dir, get_plugins_dir


class ShareManager:
    """插件导入导出管理"""

    def __init__(self):
        self.pm = PluginManager()
        self.export_dir = get_export_dir()
        self.plugins_dir = get_plugins_dir()

    def export_plugin(self, plugin_id: str) -> str:
        """将插件打包为 zip 文件（含 requirements.txt），返回 zip 路径"""
        meta = self.pm.get_plugin_meta(plugin_id)
        if not meta:
            raise ValueError(f"插件 {plugin_id} 不存在")

        plugin_dir = self.pm._plugins[plugin_id]["dir"]
        if not os.path.isdir(plugin_dir):
            raise ValueError(f"插件目录不存在: {plugin_dir}")

        zip_name = f"{plugin_id}_v{meta.get('version', '1.0.0')}.zip"
        zip_path = os.path.join(self.export_dir, zip_name)

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(plugin_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, plugin_dir)
                    zf.write(file_path, arcname)

            # 自动生成 requirements.txt（从 plugin.json 的 dependencies）
            dependencies = meta.get("dependencies", [])
            if dependencies:
                import io
                req_content = "\n".join(dependencies) + "\n"
                zf.writestr("requirements.txt", req_content)

        return zip_path

    def import_plugin(self, zip_path: str) -> str:
        """从 zip 文件导入插件，返回 plugin_id"""
        if not os.path.exists(zip_path):
            raise ValueError(f"文件不存在: {zip_path}")

        # 先解压到临时目录读取 plugin.json
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tmp_dir)

            manifest_path = os.path.join(tmp_dir, "plugin.json")
            if not os.path.exists(manifest_path):
                raise ValueError("无效的插件包: 缺少 plugin.json")

            import json
            with open(manifest_path, "r", encoding="utf-8") as f:
                meta = json.load(f)

            plugin_id = meta.get("id")
            if not plugin_id:
                raise ValueError("无效的插件包: plugin.json 缺少 id")

            # 复制到 plugins 目录
            dest_dir = os.path.join(self.plugins_dir, plugin_id)
            if os.path.exists(dest_dir):
                shutil.rmtree(dest_dir)
            shutil.copytree(tmp_dir, dest_dir)

        # 重新发现插件
        self.pm.discover_plugins()
        return plugin_id

    def list_exported(self) -> list:
        """列出已导出的插件包"""
        if not os.path.isdir(self.export_dir):
            return []
        return [
            f for f in os.listdir(self.export_dir)
            if f.endswith(".zip")
        ]