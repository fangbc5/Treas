# -*- mode: python ; coding: utf-8 -*-
"""Treas 淼淼百宝箱 - PyInstaller 打包配置

macOS:
    pyinstaller Treas.spec
    → dist/Treas.app

Windows:
    pyinstaller Treas.spec
    → dist/Treas/
"""

import sys
import os

block_cipher = None

# ============ Analysis ============
a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # 内置插件（打包到 _MEIPASS 中，只读）
        ('src/plugins', 'src/plugins'),
        # 图标资源
        ('resources/icon_1024.png', 'resources'),
        ('resources/icon.ico', 'resources'),
    ],
    hiddenimports=[
        'src',
        'src.core',
        'src.core.plugin_base',
        'src.core.plugin_manager',
        'src.core.database',
        'src.core.paths',
        'src.core.category_manager',
        'src.core.share_manager',
        'src.core.dependency_manager',
        'src.utils',
        'src.utils.icons',
        'src.utils.flow_layout',
        'src.views',
        'src.views.main_window',
        'src.views.tool_card',
        'src.views.plugin_window',
        'src.views.category_dialog',
        'src.views.add_tool_dialog',
        'src.plugins',
        'src.plugins.calculator',
        'src.plugins.calculator.widget',
        'src.plugins.currency_converter',
        'src.plugins.currency_converter.widget',
        'src.plugins.simple_ledger',
        'src.plugins.simple_ledger.widget',
        'src.plugins.social_insurance',
        'packaging',
        'packaging.specifiers',
        'packaging.version',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['build_hooks/runtime_hook.py'],
    excludes=[
        'tkinter', 'matplotlib', 'numpy', 'pandas',
        'scipy', 'PIL', 'cv2', 'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ============ 跨平台打包 ============
if sys.platform == 'darwin':
    # ---- macOS: 生成 .app ----
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='Treas',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        icon='resources/icon.icns',
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='Treas',
    )

    app = BUNDLE(
        coll,
        name='Treas.app',
        icon='resources/icon.icns',
        bundle_identifier='com.treas.app',
        info_plist={
            'CFBundleName': 'Treas',
            'CFBundleDisplayName': 'Treas - 淼淼百宝箱',
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0.0',
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '10.13.0',
            'CFBundleIdentifier': 'com.treas.app',
        },
    )

elif sys.platform == 'win32':
    # ---- Windows: 生成目录 ----
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='Treas',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        icon='resources/icon.ico',
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='Treas',
    )

else:
    # ---- Linux: 生成目录 ----
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='Treas',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='Treas',
    )