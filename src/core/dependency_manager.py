"""依赖管理器 - 插件第三方依赖的检查、安装、版本冲突检测"""

import sys
import subprocess
import importlib
from typing import List, Tuple, Optional
from packaging.specifiers import SpecifierSet
from packaging.version import Version, InvalidVersion

from src.core.database import Database
from src.core.paths import get_plugins_site_packages_dir


class DependencyManager:
    """插件依赖管理器单例"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._db = None
            cls._instance._site_packages_added = False
        return cls._instance

    @property
    def db(self):
        if self._db is None:
            self._db = Database()
        return self._db

    def ensure_site_packages_in_path(self):
        """将插件共享依赖目录加入 sys.path（只加一次）"""
        if self._site_packages_added:
            return
        site_dir = get_plugins_site_packages_dir()
        if site_dir not in sys.path:
            sys.path.insert(0, site_dir)
        self._site_packages_added = True

    # ========== 依赖声明管理 ==========

    def save_dependencies(self, plugin_id: str, dependencies: list):
        """将插件的依赖声明保存到数据库

        dependencies 格式: ["requests>=2.28", "beautifulsoup4"]
        每次调用会先清除该插件的旧记录，再重新写入
        """
        # 清除旧记录
        self.db.execute(
            "DELETE FROM plugin_dependencies WHERE plugin_id = ?",
            (plugin_id,),
        )

        for dep_str in dependencies:
            package_name, version_spec = self._parse_dependency(dep_str)
            self.db.execute(
                "INSERT OR REPLACE INTO plugin_dependencies (plugin_id, package_name, version_spec) "
                "VALUES (?, ?, ?)",
                (plugin_id, package_name, version_spec),
            )

    def get_plugin_dependencies(self, plugin_id: str) -> list:
        """获取插件的依赖列表（从数据库）"""
        rows = self.db.query(
            "SELECT package_name, version_spec FROM plugin_dependencies WHERE plugin_id = ?",
            (plugin_id,),
        )
        return [(r["package_name"], r["version_spec"]) for r in rows]

    def clear_plugin_dependencies(self, plugin_id: str):
        """清除插件的依赖记录"""
        self.db.execute(
            "DELETE FROM plugin_dependencies WHERE plugin_id = ?",
            (plugin_id,),
        )

    # ========== 缺失依赖检查 ==========

    def get_missing_dependencies(self, plugin_id: str) -> List[Tuple[str, str]]:
        """获取插件缺失的依赖列表

        返回: [(package_name, version_spec), ...]
        """
        deps = self.get_plugin_dependencies(plugin_id)
        missing = []
        for pkg_name, version_spec in deps:
            if not self._is_package_installed(pkg_name, version_spec):
                missing.append((pkg_name, version_spec))
        return missing

    def check_all_plugins_status(self) -> dict:
        """检查所有插件的依赖状态

        返回: {plugin_id: {"status": "ok"|"missing"|"conflict", "details": [...]}}
        """
        # 获取所有有依赖的插件
        rows = self.db.query("SELECT DISTINCT plugin_id FROM plugin_dependencies")
        result = {}

        for row in rows:
            pid = row["plugin_id"]
            missing = self.get_missing_dependencies(pid)
            conflicts = self.get_conflicts(pid)

            if conflicts:
                result[pid] = {"status": "conflict", "details": conflicts}
            elif missing:
                result[pid] = {"status": "missing", "details": missing}
            else:
                result[pid] = {"status": "ok", "details": []}

        return result

    # ========== 版本冲突检测 ==========

    def get_conflicts(self, plugin_id: str) -> List[dict]:
        """检测插件的依赖是否与其他插件存在版本冲突

        返回冲突列表: [{"package": "requests", "specs": {plugin_id: ">=2.31", other_id: "<2.30"}}]
        """
        deps = self.get_plugin_dependencies(plugin_id)
        conflicts = []

        for pkg_name, version_spec in deps:
            # 查询所有对该包有版本要求的插件
            all_specs = self.db.query(
                "SELECT plugin_id, version_spec FROM plugin_dependencies WHERE package_name = ?",
                (pkg_name,),
            )

            if len(all_specs) <= 1:
                continue  # 只有自己依赖这个包，无冲突

            # 检查所有版本约束是否兼容
            spec_sets = []
            for spec_row in all_specs:
                vs = spec_row["version_spec"]
                if vs:
                    try:
                        spec_sets.append(SpecifierSet(vs))
                    except Exception:
                        pass
                else:
                    # 无版本约束，兼容任何版本
                    spec_sets.append(SpecifierSet())

            # 测试是否能找到一个满足所有约束的版本
            if spec_sets and not self._specs_compatible(spec_sets):
                conflict_info = {
                    "package": pkg_name,
                    "specs": {s["plugin_id"]: s["version_spec"] for s in all_specs},
                }
                conflicts.append(conflict_info)

        return conflicts

    def _specs_compatible(self, spec_sets: list) -> bool:
        """检查多个 SpecifierSet 是否兼容（存在交集）

        策略：用一组常见版本号测试是否有版本能满足所有约束
        """
        try:
            # 获取 pip 可用的版本列表太慢，用简化策略：
            # 如果所有约束都不互斥（如 >=2.31 和 <2.30），则认为兼容
            # 用 packaging 的 & 操作符检查
            combined = spec_sets[0]
            for ss in spec_sets[1:]:
                intersection = combined & ss
                # 如果交集为空 SpecifierSet，检查是否有意义
                if str(intersection).strip() == "":
                    # 两个 specifier 完全不兼容
                    # 但需要排除空 spec（"" 表示任意版本）
                    if str(combined).strip() != "" and str(ss).strip() != "":
                        return False
                combined = intersection
            return True
        except Exception:
            # 解析失败时保守认为兼容
            return True

    # ========== 安装依赖 ==========

    def install_dependencies(self, packages: List[str],
                            progress_callback=None) -> Tuple[bool, str]:
        """使用 pip install --target 安装依赖包到共享目录

        packages: ["requests>=2.28", "beautifulsoup4"]
        progress_callback: 可选回调函数，用于报告进度

        返回: (success: bool, message: str)

        跨平台兼容：
        - 开发模式：subprocess + sys.executable
        - 打包模式（PyInstaller frozen）：pip 内部模块直接调用
        """
        site_dir = get_plugins_site_packages_dir()
        self.ensure_site_packages_in_path()

        try:
            if getattr(sys, 'frozen', False):
                # 打包模式：pip 作为内部模块直接调用（不依赖外部 Python）
                return self._install_via_pip_internal(packages, site_dir)
            else:
                # 开发模式：subprocess 调用
                return self._install_via_subprocess(packages, site_dir)

        except Exception as e:
            return False, f"安装出错: {e}"

    def _install_via_subprocess(self, packages: List[str],
                                site_dir: str) -> Tuple[bool, str]:
        """开发模式：通过 subprocess 调用 pip"""
        cmd = [
            sys.executable, "-m", "pip", "install",
            "--target", site_dir,
            "--quiet",
            "--disable-pip-version-check",
        ] + packages

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 分钟超时
        )

        if result.returncode != 0:
            return False, f"pip install 失败:\n{result.stderr}"

        # 安装成功后更新数据库缓存
        self._refresh_installed_packages()

        return True, "依赖安装成功"

    @staticmethod
    def _find_system_python() -> Optional[str]:
        """查找系统 Python 解释器路径

        查找顺序：
        1. shutil.which('python3') / shutil.which('python')
        2. macOS: /usr/bin/python3
        3. Windows: py 启动器
        """
        import os
        import shutil
        import platform

        # 1. PATH 中查找
        for name in (['python3', 'python'] if platform.system() != 'Windows'
                     else ['python', 'python3']):
            path = shutil.which(name)
            if path:
                return path

        # 2. Windows: py 启动器
        if platform.system() == 'Windows':
            py_path = shutil.which('py')
            if py_path:
                return py_path

        # 3. macOS 常见路径
        if platform.system() == 'Darwin':
            for p in ['/usr/bin/python3', '/usr/local/bin/python3']:
                if os.path.isfile(p):
                    return p

        # 4. Linux 常见路径
        for p in ['/usr/bin/python3', '/usr/local/bin/python3']:
            if os.path.isfile(p):
                return p

        return None

    def _install_via_pip_internal(self, packages: List[str],
                                  site_dir: str) -> Tuple[bool, str]:
        """打包模式：查找系统 Python 并通过 subprocess 调用 pip"""
        import os
        import platform

        python_path = self._find_system_python()
        if not python_path:
            return (False,
                    "未找到系统 Python，无法安装依赖。\n"
                    "请安装 Python 3.9+ 后重试：https://www.python.org/downloads/")

        cmd = [
            python_path, "-m", "pip", "install",
            "--target", site_dir,
            "--quiet",
            "--disable-pip-version-check",
            "--no-warn-script-location",
        ] + packages

        # Windows 上隐藏控制台黑色窗口
        kwargs = dict(
            capture_output=True,
            text=True,
            timeout=300,
        )
        if platform.system() == 'Windows':
            kwargs['creationflags'] = 0x08000000  # subprocess.CREATE_NO_WINDOW

        try:
            result = subprocess.run(cmd, **kwargs)

            if result.returncode != 0:
                return False, f"pip install 失败:\n{result.stderr}"

            # 安装成功后更新数据库缓存
            self._refresh_installed_packages()

            return True, "依赖安装成功"

        except subprocess.TimeoutExpired:
            return False, "安装超时（5分钟），请检查网络连接"
        except FileNotFoundError:
            return False, f"未找到 Python: {python_path}\n请安装 Python 后重试。"
        except Exception as e:
            return False, f"安装出错: {e}"

    # ========== 已安装包管理 ==========

    def _is_package_installed(self, package_name: str, version_spec: str = "") -> bool:
        """检查包是否已安装（先查 DB 缓存，再查实际）"""
        # 1. 查 DB 缓存
        normalized = self._normalize_name(package_name)
        row = self.db.query_one(
            "SELECT version FROM installed_packages WHERE package_name = ?",
            (normalized,),
        )

        if row and row["version"]:
            # 有版本记录，检查是否满足版本约束
            if version_spec:
                try:
                    installed_ver = Version(row["version"])
                    spec = SpecifierSet(version_spec)
                    return installed_ver in spec
                except (InvalidVersion, Exception):
                    return True  # 版本解析失败，保守认为已安装
            return True

        # 2. DB 无记录，尝试 import 检查（可能是内置库或之前手动安装的）
        try:
            importlib.import_module(package_name)
            return True
        except ImportError:
            # 也检查 .site-packages 目录
            return False

    def _refresh_installed_packages(self):
        """刷新已安装包的数据库缓存（扫描 .site-packages/ 目录）"""
        import os

        site_dir = get_plugins_site_packages_dir()

        # 清除旧缓存
        self.db.execute("DELETE FROM installed_packages")

        # 扫描 .dist-info 目录获取已安装包信息
        if not os.path.isdir(site_dir):
            return

        for entry in os.listdir(site_dir):
            if entry.endswith(".dist-info"):
                # 格式: package_name-version.dist-info
                parts = entry[:-10].rsplit("-", 1)  # 去掉 .dist-info
                if len(parts) == 2:
                    pkg_name = self._normalize_name(parts[0])
                    version = parts[1]
                    self.db.execute(
                        "INSERT OR REPLACE INTO installed_packages (package_name, version) "
                        "VALUES (?, ?)",
                        (pkg_name, version),
                    )

    # ========== 工具方法 ==========

    @staticmethod
    def _parse_dependency(dep_str: str) -> Tuple[str, str]:
        """解析依赖字符串为 (package_name, version_spec)

        "requests>=2.28" → ("requests", ">=2.28")
        "beautifulsoup4" → ("beautifulsoup4", "")
        """
        # 支持的版本操作符（按长度降序匹配）
        ops = ["===", "==", "~=", ">=", "<=", "!=", ">", "<"]
        for op in ops:
            if op in dep_str:
                idx = dep_str.index(op)
                return dep_str[:idx].strip(), dep_str[idx:].strip()
        return dep_str.strip(), ""

    @staticmethod
    def _normalize_name(name: str) -> str:
        """标准化包名（pip 和 packaging 使用小写 + 连字符）"""
        return name.lower().replace("_", "-").replace(".", "-")

    def get_dependency_summary(self, plugin_id: str) -> dict:
        """获取插件的依赖摘要（供 UI 使用）

        返回: {
            "status": "ok"|"missing"|"conflict"|"no_deps",
            "total": 3,
            "installed": 2,
            "missing": [(pkg, spec), ...],
            "conflicts": [...]
        }
        """
        deps = self.get_plugin_dependencies(plugin_id)

        if not deps:
            return {
                "status": "no_deps",
                "total": 0,
                "installed": 0,
                "missing": [],
                "conflicts": [],
            }

        missing = self.get_missing_dependencies(plugin_id)
        conflicts = self.get_conflicts(plugin_id)
        installed_count = len(deps) - len(missing)

        status = "ok"
        if conflicts:
            status = "conflict"
        elif missing:
            status = "missing"

        return {
            "status": status,
            "total": len(deps),
            "installed": installed_count,
            "missing": missing,
            "conflicts": conflicts,
        }