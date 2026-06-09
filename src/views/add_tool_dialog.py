"""添加工具到分类的对话框 - 支持多选"""

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy,
    QListWidget, QListWidgetItem,
)
from PyQt5.QtCore import Qt

from qfluentwidgets import (
    MessageBoxBase, SubtitleLabel, CaptionLabel,
    PrimaryPushButton, PushButton, FluentIcon,
    CheckBox,
)


class AddToolDialog(MessageBoxBase):
    """添加工具到分类 - 多选列表对话框"""

    def __init__(self, parent=None, category_name: str = "", uncategorized_tools: list = None):
        super().__init__(parent)
        self._tools = uncategorized_tools or []
        self._category_name = category_name
        self._checkboxes = []
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("添加工具到分类")

        # 内容区域（viewLayout 是 MessageBoxBase 自带的 QVBoxLayout）
        layout = self.viewLayout
        layout.setSpacing(12)

        # 标题
        title = SubtitleLabel(f"选择要加入「{self._category_name}」的工具")
        layout.addWidget(title)

        # 提示
        if not self._tools:
            hint = CaptionLabel("暂无未分类的工具，请先导入插件或将工具移出当前分类。")
            hint.setStyleSheet("color: gray;")
            layout.addWidget(hint)
            # 隐藏确定按钮
            self.yesButton.setEnabled(False)
            return

        hint = CaptionLabel(f"共 {len(self._tools)} 个未分类工具，勾选后点击确定添加到当前分类。")
        hint.setStyleSheet("color: gray;")
        layout.addWidget(hint)

        # 全选 / 取消全选
        select_layout = QHBoxLayout()
        select_all_btn = PushButton("全选")
        select_all_btn.setFixedWidth(80)
        deselect_all_btn = PushButton("取消全选")
        deselect_all_btn.setFixedWidth(80)
        select_layout.addWidget(select_all_btn)
        select_layout.addWidget(deselect_all_btn)
        select_layout.addStretch()
        layout.addLayout(select_layout)

        # 工具列表（带复选框）
        self._list_widget = QListWidget()
        self._list_widget.setMinimumHeight(200)
        self._list_widget.setMaximumHeight(400)

        for tool in self._tools:
            item = QListWidgetItem()
            cb = CheckBox(f"  {tool.get('name', tool['id'])}  -  {tool.get('description', '无描述')}")
            cb.setProperty("tool_id", tool["id"])
            cb.setProperty("tool_name", tool.get("name", tool["id"]))
            self._checkboxes.append(cb)

            item.setSizeHint(cb.sizeHint())
            self._list_widget.addItem(item)
            self._list_widget.setItemWidget(item, cb)

        layout.addWidget(self._list_widget)

        # 全选/取消全选事件
        select_all_btn.clicked.connect(self._select_all)
        deselect_all_btn.clicked.connect(self._deselect_all)

        # 按钮文字
        self.yesButton.setText("添加")
        self.cancelButton.setText("取消")

    def _select_all(self):
        for cb in self._checkboxes:
            cb.setChecked(True)

    def _deselect_all(self):
        for cb in self._checkboxes:
            cb.setChecked(False)

    def get_selected_tools(self) -> list:
        """返回选中的工具列表 [{id, name}, ...]"""
        result = []
        for cb in self._checkboxes:
            if cb.isChecked():
                result.append({
                    "id": cb.property("tool_id"),
                    "name": cb.property("tool_name"),
                })
        return result