"""工具卡片组件 - 基于 QFluentWidgets CardWidget"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy

from qfluentwidgets import (
    CardWidget, StrongBodyLabel, CaptionLabel,
    PushButton, PrimaryPushButton, ToolButton, FluentIcon,
)

from src.utils.icons import fluent_icon_from_name


class ToolCard(CardWidget):
    """工具卡片 - Fluent 风格"""

    open_requested = pyqtSignal(str)
    export_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)

    def __init__(self, plugin_meta: dict, parent=None):
        super().__init__(parent)
        self.plugin_meta = plugin_meta
        self.plugin_id = plugin_meta.get("id", "")
        self.is_builtin = plugin_meta.get("is_builtin", False)
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

        # 描述
        desc = self.plugin_meta.get("description", "")
        if desc:
            desc_label = CaptionLabel(desc)
            desc_label.setWordWrap(True)
            desc_label.setMaximumHeight(40)
            layout.addWidget(desc_label)

        # 版本
        version = self.plugin_meta.get("version", "")
        if version:
            ver_label = CaptionLabel(f"v{version}")
            layout.addWidget(ver_label)

        layout.addStretch()

        # 底部按钮
        btn_layout = QHBoxLayout()

        open_btn = PrimaryPushButton("打开")
        open_btn.setIcon(FluentIcon.PLAY)
        open_btn.clicked.connect(lambda: self.open_requested.emit(self.plugin_id))
        btn_layout.addWidget(open_btn)

        share_btn = ToolButton(FluentIcon.SHARE)
        share_btn.setToolTip("分享插件")
        share_btn.clicked.connect(lambda: self.export_requested.emit(self.plugin_id))
        btn_layout.addWidget(share_btn)

        delete_btn = ToolButton(FluentIcon.DELETE)
        delete_btn.setToolTip("删除插件")
        delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.plugin_id))
        btn_layout.addWidget(delete_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.setFixedWidth(220)
        self.setMinimumHeight(180)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)