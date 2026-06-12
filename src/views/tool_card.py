"""工具卡片组件 - 基于 QFluentWidgets CardWidget"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFontMetrics
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy


from qfluentwidgets import (
    CardWidget, StrongBodyLabel, CaptionLabel,
    PushButton, ToolButton, FluentIcon,
)

from src.utils.icons import fluent_icon_from_name


class AddToolCard(CardWidget):
    """添加工具卡片 - 点击可添加工具到当前分类"""

    add_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.clicked.connect(lambda: self.add_requested.emit())

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setAlignment(Qt.AlignCenter)

        # 加号图标
        add_label = QLabel()
        add_icon = FluentIcon.ADD.icon()
        add_label.setPixmap(add_icon.pixmap(40, 40))
        add_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(add_label)

        # 提示文字
        hint_label = CaptionLabel("添加工具")
        hint_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint_label)

        self.setFixedWidth(220)
        self.setMinimumHeight(180)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # 虚线边框样式
        self.setStyleSheet("""
            AddToolCard {
                border: 2px dashed #ccc;
                border-radius: 8px;
                background: transparent;
            }
            AddToolCard:hover {
                border-color: #4a90d9;
                background: rgba(74, 144, 217, 0.05);
            }
        """)


class ToolCard(CardWidget):
    """工具卡片 - Fluent 风格"""

    open_requested = pyqtSignal(str)
    export_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    change_category_requested = pyqtSignal(str)
    install_deps_requested = pyqtSignal(str)

    def __init__(self, plugin_meta: dict, parent=None):
        super().__init__(parent)
        self.plugin_meta = plugin_meta
        self.plugin_id = plugin_meta.get("id", "")
        self.is_builtin = plugin_meta.get("is_builtin", False)
        self._dep_summary = plugin_meta.get("_dep_summary", {})
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)

        # 图标 + 名称行
        top_layout = QHBoxLayout()

        # 图标
        icon_name = self.plugin_meta.get("icon", "APPLICATION")
        icon = fluent_icon_from_name(icon_name)
        icon_label = QLabel()
        icon_label.setPixmap(icon.icon().pixmap(40, 40))
        top_layout.addWidget(icon_label)

        # 名称
        name_label = StrongBodyLabel(self.plugin_meta.get("name", "未命名"))
        name_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        top_layout.addWidget(name_label)
        top_layout.addStretch()

        layout.addLayout(top_layout)

        # 描述（双行省略，hover 显示完整内容，避免高度被遮挡）
        desc = self.plugin_meta.get("description", "")
        if desc:
            desc_label = CaptionLabel()
            desc_label.setWordWrap(True)
            fm = QFontMetrics(desc_label.font())
            text_width = 188  # 卡片宽度 220 - 左右 padding 32
            max_lines = 2
            line_height = fm.lineSpacing()
            max_height = line_height * max_lines
            desc_label.setFixedHeight(max_height)
            # 计算文本在双行内是否溢出，溢出则截断并加省略号
            # 注意：高度参数传很大的值，让 boundingRect 返回文本自然高度
            natural_rect = fm.boundingRect(
                0, 0, text_width, 100000,
                int(Qt.TextFlag.TextWordWrap), desc,
            )
            if natural_rect.height() > max_height:
                elided = desc
                ellipsis = "…"
                # 逐步删减最后一个字符直到能放入双行（含省略号）
                while elided and fm.boundingRect(
                    0, 0, text_width, 100000,
                    int(Qt.TextFlag.TextWordWrap), elided + ellipsis,
                ).height() > max_height:
                    elided = elided[:-1]
                desc_label.setText(elided.rstrip() + ellipsis)
            else:
                desc_label.setText(desc)
            # hover 显示完整描述
            desc_label.setToolTip(desc)
            layout.addWidget(desc_label)

        # 版本
        version = self.plugin_meta.get("version", "")
        if version:
            ver_label = CaptionLabel(f"v{version}")
            layout.addWidget(ver_label)

        # 依赖状态提示
        dep_status = self._dep_summary.get("status", "no_deps")
        if dep_status == "missing":
            missing = self._dep_summary.get("missing", [])
            pkg_names = ", ".join(p[0] for p in missing)
            dep_label = CaptionLabel(f"⚠️ 缺少依赖: {pkg_names}")
            dep_label.setStyleSheet("color: #e67e22; font-size: 11px;")
            dep_label.setWordWrap(True)
            layout.addWidget(dep_label)

            # 安装依赖按钮
            install_btn = PushButton("安装依赖")
            install_btn.setFixedHeight(26)
            install_btn.setStyleSheet("font-size: 11px;")
            install_btn.clicked.connect(
                lambda: self.install_deps_requested.emit(self.plugin_id)
            )
            layout.addWidget(install_btn)

        elif dep_status == "conflict":
            conflicts = self._dep_summary.get("conflicts", [])
            pkg_names = ", ".join(c["package"] for c in conflicts)
            dep_label = CaptionLabel(f"🔴 依赖冲突: {pkg_names}")
            dep_label.setStyleSheet("color: #e74c3c; font-size: 11px;")
            dep_label.setWordWrap(True)
            layout.addWidget(dep_label)

        layout.addStretch()

        # 底部按钮
        btn_layout = QHBoxLayout()

        # 依赖缺失时禁用打开按钮
        open_btn = ToolButton(FluentIcon.PLAY)
        open_btn.setToolTip("打开")
        open_btn.setEnabled(dep_status != "missing")
        open_btn.clicked.connect(lambda: self.open_requested.emit(self.plugin_id))
        btn_layout.addWidget(open_btn)

        # 内置工具不显示分享按钮
        if not self.is_builtin:
            share_btn = ToolButton(FluentIcon.SHARE)
            share_btn.setToolTip("分享插件")
            share_btn.clicked.connect(lambda: self.export_requested.emit(self.plugin_id))
            btn_layout.addWidget(share_btn)

        delete_btn = ToolButton(FluentIcon.DELETE)
        delete_btn.setToolTip("删除插件")
        delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.plugin_id))
        btn_layout.addWidget(delete_btn)

        category_btn = ToolButton(FluentIcon.MENU)
        category_btn.setToolTip("修改分类")
        category_btn.clicked.connect(lambda: self.change_category_requested.emit(self.plugin_id))
        btn_layout.addWidget(category_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.setFixedWidth(220)
        self.setMinimumHeight(180)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)