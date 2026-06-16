"""HTTP 客户端 - 小型可复用组件"""

import json

from PyQt5.QtWidgets import (
    QWidget, QHeaderView, QTableWidgetItem,
    QFormLayout, QAbstractItemView, QVBoxLayout, QHBoxLayout,
)
from PyQt5.QtCore import Qt, QTimer, QPointF
from PyQt5.QtGui import QColor, QPolygonF, QPainter, QPalette

from qfluentwidgets import (
    PushButton, LineEdit, StrongBodyLabel, CaptionLabel, InfoBar,
    ComboBox, TextEdit, TableWidget, CheckBox,
    TreeWidget as FluentTreeWidgetBase,
)
from qfluentwidgets.components.widgets.tree_view import TreeItemDelegate

from constants import (
    METHOD_COLORS, BODY_TYPES, BODY_TYPE_LABELS, AUTH_TYPES, AUTH_TYPE_LABELS,
)


class _ReadableTreeItemDelegate(TreeItemDelegate):
    """自定义 delegate：强制选中态文字保持深色（可读）。

    qfluentwidgets 的 TreeItemDelegate.initStyleOption 会根据 isDarkTheme()
    覆盖文字颜色，导致在浅色主题下选中文字变白不可见。这里重写后始终使用
    item 自身的前景色（由 setForeground 设置），保证选中态可见。
    """

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)

        # 优先使用 item 的 foreground（如请求方法的颜色），否则深灰
        brush = index.data(Qt.ForegroundRole)
        if brush is not None:
            color = brush.color()
        else:
            color = QColor("#212121")

        option.palette.setColor(QPalette.Text, color)
        option.palette.setColor(QPalette.HighlightedText, color)


class FluentTreeWidget(FluentTreeWidgetBase):
    """基于 qfluentwidgets.TreeWidget 的自定义树形控件。

    解决两个问题：
    1. 选中集合名称变白看不见 —— 通过自定义 delegate 强制文字颜色。
    2. 左侧展开三角变蓝 —— 重写 drawBranches 且不调 super，自绘柔和灰色三角，
       彻底阻断 macOS 原生蓝色箭头（无需额外 QSS，避免与 qfluentwidgets 样式
       冲突导致内容整体右移）。
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # 强制文字可读（关键修复：替换默认 delegate，防止选中态文字变白）
        self.setItemDelegate(_ReadableTreeItemDelegate(self))

    def drawBranches(self, painter, rect, index):
        """自绘柔和灰色三角，并阻止基类绘制原生蓝色箭头。"""
        # 不调用 super().drawBranches()，彻底阻断 macOS 原生箭头
        item = self.itemFromIndex(index)
        if item is None:
            return

        # 只为有子项的节点绘制三角
        if item.childCount() == 0:
            return

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        # 始终使用柔和灰色，避免任何蓝色/紫色（符合用户预期）
        from qfluentwidgets.common.style_sheet import isDarkTheme
        color = QColor("#c0c4cc") if isDarkTheme() else QColor("#9aa0a6")
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)

        cx = rect.center().x()
        cy = rect.center().y()
        sz = 4.5

        if self.isExpanded(index):
            # 向下的三角（展开状态）
            painter.drawPolygon(QPolygonF([
                QPointF(cx - sz, cy - sz * 0.5),
                QPointF(cx + sz, cy - sz * 0.5),
                QPointF(cx, cy + sz * 0.6),
            ]))
        else:
            # 向右的三角（折叠状态）
            painter.drawPolygon(QPolygonF([
                QPointF(cx - sz * 0.4, cy - sz),
                QPointF(cx + sz * 0.7, cy),
                QPointF(cx - sz * 0.4, cy + sz),
            ]))

        painter.restore()


class KeyValueTable(QWidget):
    """Key-Value 编辑器（用于 Params / Headers）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.table = TableWidget()
        self.table.setRowCount(0)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["启用", "Key", "Value"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 200)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        add_btn = PushButton("添加行")
        add_btn.setFixedHeight(28)
        add_btn.clicked.connect(self._add_row)
        btn_layout.addWidget(add_btn)

        clear_btn = PushButton("清空")
        clear_btn.setFixedHeight(28)
        clear_btn.clicked.connect(self._clear_all)
        btn_layout.addWidget(clear_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self._add_row()

    def _add_row(self, key="", value="", enabled=True):
        row = self.table.rowCount()
        self.table.insertRow(row)

        check = CheckBox()
        check.setChecked(enabled)
        self.table.setCellWidget(row, 0, check)

        self.table.setItem(row, 1, QTableWidgetItem(key))
        self.table.setItem(row, 2, QTableWidgetItem(value))

    def _clear_all(self):
        self.table.setRowCount(0)
        self._add_row()

    def get_data(self) -> list:
        result = []
        for row in range(self.table.rowCount()):
            check = self.table.cellWidget(row, 0)
            key_item = self.table.item(row, 1)
            value_item = self.table.item(row, 2)

            if key_item and key_item.text().strip():
                result.append({
                    "key": key_item.text().strip(),
                    "value": value_item.text() if value_item else "",
                    "enabled": check.isChecked() if check else True,
                })
        return result

    def set_data(self, data: list):
        self.table.setRowCount(0)
        for item in data:
            self._add_row(
                key=item.get("key", ""),
                value=item.get("value", ""),
                enabled=item.get("enabled", True),
            )
        if self.table.rowCount() == 0:
            self._add_row()


class AuthPanel(QWidget):
    """认证配置面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        type_layout = QHBoxLayout()
        type_label = StrongBodyLabel("认证类型:")
        type_label.setFixedWidth(80)
        self.type_combo = ComboBox()
        self.type_combo.addItems([AUTH_TYPE_LABELS[t] for t in AUTH_TYPES])
        self.type_combo.setFixedWidth(200)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_combo)
        type_layout.addStretch()
        layout.addLayout(type_layout)

        self.config_widget = QWidget()
        self.config_layout = QVBoxLayout(self.config_widget)
        self.config_layout.setContentsMargins(0, 0, 0, 0)
        self.config_layout.setSpacing(8)
        layout.addWidget(self.config_widget)

        layout.addStretch()
        self._on_type_changed(0)

    def _on_type_changed(self, index):
        self._clear_layout(self.config_layout)

        auth_type = AUTH_TYPES[index] if index < len(AUTH_TYPES) else "none"

        if auth_type == "basic":
            form = QFormLayout()
            self.username_input = LineEdit()
            self.username_input.setPlaceholderText("用户名")
            form.addRow("用户名:", self.username_input)
            self.password_input = LineEdit()
            self.password_input.setPlaceholderText("密码")
            self.password_input.setEchoMode(LineEdit.Password)
            form.addRow("密码:", self.password_input)
            self.config_layout.addLayout(form)

        elif auth_type == "bearer":
            form = QFormLayout()
            self.token_input = LineEdit()
            self.token_input.setPlaceholderText("Bearer Token")
            form.addRow("Token:", self.token_input)
            self.config_layout.addLayout(form)

        elif auth_type == "api_key":
            form = QFormLayout()
            self.key_name_input = LineEdit()
            self.key_name_input.setText("X-API-Key")
            self.key_name_input.setPlaceholderText("Header/参数名")
            form.addRow("Key 名称:", self.key_name_input)
            self.key_value_input = LineEdit()
            self.key_value_input.setPlaceholderText("API Key 值")
            form.addRow("Key 值:", self.key_value_input)
            self.add_to_combo = ComboBox()
            self.add_to_combo.addItems(["Header", "Query 参数"])
            form.addRow("添加到:", self.add_to_combo)
            self.config_layout.addLayout(form)

        else:
            hint = CaptionLabel("当前请求不使用认证")
            hint.setStyleSheet("color: #999; padding: 20px;")
            self.config_layout.addWidget(hint)

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            else:
                sub = item.layout()
                if sub:
                    AuthPanel._clear_layout(sub)

    def get_data(self) -> dict:
        auth_type = AUTH_TYPES[self.type_combo.currentIndex()] if self.type_combo.currentIndex() < len(AUTH_TYPES) else "none"
        config = {"type": auth_type}

        if auth_type == "basic" and hasattr(self, "username_input"):
            config["username"] = self.username_input.text()
            config["password"] = self.password_input.text()
        elif auth_type == "bearer" and hasattr(self, "token_input"):
            config["token"] = self.token_input.text()
        elif auth_type == "api_key" and hasattr(self, "key_name_input"):
            config["key_name"] = self.key_name_input.text()
            config["key_value"] = self.key_value_input.text()
            config["add_to"] = "header" if self.add_to_combo.currentIndex() == 0 else "query"

        return config

    def set_data(self, data: dict):
        if not data:
            return
        auth_type = data.get("type", "none")
        if auth_type in AUTH_TYPES:
            self.type_combo.setCurrentIndex(AUTH_TYPES.index(auth_type))
        QTimer.singleShot(50, lambda: self._set_values(data))

    def _set_values(self, data: dict):
        auth_type = data.get("type", "none")
        if auth_type == "basic" and hasattr(self, "username_input"):
            self.username_input.setText(data.get("username", ""))
            self.password_input.setText(data.get("password", ""))
        elif auth_type == "bearer" and hasattr(self, "token_input"):
            self.token_input.setText(data.get("token", ""))
        elif auth_type == "api_key" and hasattr(self, "key_name_input"):
            self.key_name_input.setText(data.get("key_name", "X-API-Key"))
            self.key_value_input.setText(data.get("key_value", ""))
            self.add_to_combo.setCurrentIndex(0 if data.get("add_to", "header") == "header" else 1)


class BodyEditor(QWidget):
    """请求体编辑器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        type_layout = QHBoxLayout()
        type_label = StrongBodyLabel("Body 类型:")
        type_label.setFixedWidth(80)
        self.type_combo = ComboBox()
        self.type_combo.addItems([BODY_TYPE_LABELS[t] for t in BODY_TYPES])
        self.type_combo.setFixedWidth(200)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_combo)

        self.format_btn = PushButton("格式化 JSON")
        self.format_btn.setFixedHeight(28)
        self.format_btn.clicked.connect(self._format_json)
        type_layout.addWidget(self.format_btn)
        type_layout.addStretch()
        layout.addLayout(type_layout)

        self.editor = TextEdit()
        self.editor.setStyleSheet("""
            TextEdit {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px;
                font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
                font-size: 13px;
            }
        """)
        self.editor.setPlaceholderText('输入请求体内容...\nJSON 示例: {"key": "value"}')
        layout.addWidget(self.editor)

    def _on_type_changed(self, index):
        body_type = BODY_TYPES[index] if index < len(BODY_TYPES) else "none"
        self.editor.setEnabled(body_type != "none")
        self.format_btn.setVisible(body_type == "json")

        placeholders = {
            "json": '{"key": "value"}',
            "urlencoded": "key1=value1&key2=value2",
            "form_data": "表单数据（Key-Value JSON 数组）",
            "raw": "输入原始文本...",
        }
        self.editor.setPlaceholderText(placeholders.get(body_type, ""))

    def _format_json(self):
        text = self.editor.toPlainText()
        if text.strip():
            try:
                obj = json.loads(text)
                formatted = json.dumps(obj, indent=2, ensure_ascii=False)
                self.editor.setPlainText(formatted)
            except json.JSONDecodeError as e:
                InfoBar.warning("格式化失败", f"JSON 语法错误: {e}", parent=self, duration=3000)

    def get_data(self) -> tuple:
        idx = self.type_combo.currentIndex()
        body_type = BODY_TYPES[idx] if idx < len(BODY_TYPES) else "none"
        return body_type, self.editor.toPlainText()

    def set_data(self, body_type: str, content: str):
        if body_type in BODY_TYPES:
            self.type_combo.setCurrentIndex(BODY_TYPES.index(body_type))
        self.editor.setPlainText(content or "")