"""分类对话框 - 基于 QDialog + Fluent 组件"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLineEdit, QLabel, QPushButton,
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QColor, QPalette

from qfluentwidgets import (
    PrimaryPushButton, PushButton, FluentIcon,
    StrongBodyLabel, CaptionLabel, ToolButton, InfoBar,
    TransparentToolButton,
)

from src.utils.icons import CATEGORY_ICONS


class CategoryDialog(QDialog):
    """分类新建/编辑对话框"""

    def __init__(self, parent=None, category: dict = None):
        super().__init__(parent)
        self.category = category
        self._selected_icon = category["icon"] if category else "FOLDER"
        self._action = "save"
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("编辑分类" if self.category else "新建分类")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 16)

        # 名称
        name_label = StrongBodyLabel("分类名称")
        layout.addWidget(name_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("输入分类名称")
        self.name_input.setMinimumHeight(36)
        if self.category:
            self.name_input.setText(self.category["name"])
        layout.addWidget(self.name_input)

        # 图标选择
        icon_title = StrongBodyLabel("选择图标")
        layout.addWidget(icon_title)

        icon_grid = QGridLayout()
        icon_grid.setSpacing(8)
        self.icon_buttons = []

        cols = 4
        for idx, (fluent_icon, display_name) in enumerate(CATEGORY_ICONS):
            btn = ToolButton(fluent_icon)
            btn.setFixedSize(44, 44)
            btn.setToolTip(display_name)
            btn.setIconSize(QSize(24, 24))
            btn.clicked.connect(
                lambda checked, name=fluent_icon.name: self._select_icon(name)
            )
            # 标记选中
            if fluent_icon.name == self._selected_icon:
                btn.setStyleSheet(
                    "ToolButton { border: 2px solid #4a90d9; border-radius: 6px; }"
                )
            self.icon_buttons.append((btn, fluent_icon.name))
            row = idx // cols
            col = idx % cols
            icon_grid.addWidget(btn, row, col)

        layout.addLayout(icon_grid)
        layout.addStretch()

        # 按钮区
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = PushButton("取消")
        cancel_btn.setIcon(FluentIcon.CANCEL)
        cancel_btn.setMinimumWidth(80)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        if self.category:
            delete_btn = PushButton("删除")
            delete_btn.setIcon(FluentIcon.DELETE)
            delete_btn.setMinimumWidth(80)
            # 用 QPalette 设置红色，不覆盖 Fluent 内部样式表
            palette = delete_btn.palette()
            palette.setColor(QPalette.ButtonText, QColor("#d32f2f"))
            palette.setColor(QPalette.Text, QColor("#d32f2f"))
            delete_btn.setPalette(palette)
            delete_btn.clicked.connect(self._mark_delete)
            btn_layout.addWidget(delete_btn)

        ok_btn = PrimaryPushButton("确定")
        ok_btn.setIcon(FluentIcon.ACCEPT)
        ok_btn.setMinimumWidth(80)
        ok_btn.clicked.connect(self._validate_and_accept)
        btn_layout.addWidget(ok_btn)

        layout.addLayout(btn_layout)

    def _select_icon(self, icon_name: str):
        self._selected_icon = icon_name
        for btn, name in self.icon_buttons:
            if name == icon_name:
                btn.setStyleSheet(
                    "ToolButton { border: 2px solid #4a90d9; border-radius: 6px; }"
                )
            else:
                btn.setStyleSheet("")

    def _validate_and_accept(self):
        if not self.name_input.text().strip():
            InfoBar.warning("提示", "请输入分类名称", parent=self, duration=2000)
            return
        self.accept()

    def _mark_delete(self):
        self._action = "delete"
        self.accept()

    def get_data(self) -> dict:
        return {
            "name": self.name_input.text().strip(),
            "icon": self._selected_icon,
            "action": self._action,
        }