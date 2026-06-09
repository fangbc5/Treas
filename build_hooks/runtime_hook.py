"""PyInstaller 运行时钩子 - 修复 darkdetect 在打包环境中的版本检测问题

darkdetect 调用 platform.mac_ver()[0] 获取 macOS 版本，
PyInstaller 打包后可能返回空字符串导致 ValueError。
此钩子在 darkdetect 加载前修补 platform.mac_ver 确保返回有效值。
"""

import sys
import platform

if sys.platform == 'darwin':
    _original_mac_ver = platform.mac_ver

    def _patched_mac_ver():
        result = _original_mac_ver()
        if not result[0]:
            # PyInstaller 环境中可能返回空字符串，回退到 subprocess 调用
            import subprocess
            try:
                output = subprocess.check_output(
                    ['sw_vers', '-productVersion'],
                    text=True, timeout=2
                ).strip()
                return (output, result[1], result[2])
            except Exception:
                # 最终回退：假定支持的版本
                return ('14.0.0', '', '')
        return result

    platform.mac_ver = _patched_mac_ver