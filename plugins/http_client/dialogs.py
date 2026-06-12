"""HTTP 客户端 - 对话框组件"""

import json

from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QHeaderView, QHBoxLayout,
    QVBoxLayout, QTreeWidgetItem, QTableWidgetItem,
    QApplication, QSizePolicy,
)
from PyQt5.QtCore import Qt

from qfluentwidgets import (
    PushButton, PrimaryPushButton, LineEdit, StrongBodyLabel, CaptionLabel,
    InfoBar, TextEdit, TableWidget,
)

from curl_parser import parse_curl
from widgets import FluentTreeWidget


class CurlImportDialog(QDialog):
    """cURL 命令导入对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parsed_data = None
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("导入 cURL 命令")
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        layout.addWidget(StrongBodyLabel("粘贴 cURL 命令:"))
        self.input = TextEdit()
        self.input.setPlaceholderText(
            'curl "https://api.example.com/data" \\\n'
            '  -H "Authorization: Bearer token" \\\n'
            '  -d \'{"key": "value"}\''
        )
        self.input.setStyleSheet("""
            TextEdit {
                font-family: "JetBrains Mono", "Consolas", monospace;
                font-size: 13px;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.input)

        self.preview_label = CaptionLabel("")
        layout.addWidget(self.preview_label)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        parse_btn = PushButton("解析")
        parse_btn.clicked.connect(self._parse)
        btn_layout.addWidget(parse_btn)

        import_btn = PrimaryPushButton("导入")
        import_btn.clicked.connect(self._import)
        btn_layout.addWidget(import_btn)

        cancel_btn = PushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def _parse(self):
        text = self.input.toPlainText().strip()
        if not text:
            self.preview_label.setText("⚠️ 请输入 cURL 命令")
            self.preview_label.setStyleSheet("color: #e67e22;")
            return

        self.parsed_data = parse_curl(text)
        if self.parsed_data:
            method = self.parsed_data.get("method", "GET")
            url = self.parsed_data.get("url", "")
            headers_count = len(self.parsed_data.get("headers", []))
            self.preview_label.setText(
                f"✅ 解析成功: {method} {url}\n"
                f"Headers: {headers_count} 个, Body: {self.parsed_data.get('body_type', 'none')}"
            )
            self.preview_label.setStyleSheet("color: #27ae60;")
        else:
            self.preview_label.setText("❌ 解析失败，请检查 cURL 命令格式")
            self.preview_label.setStyleSheet("color: #e74c3c;")

    def _import(self):
        if not self.parsed_data:
            self._parse()
        if self.parsed_data:
            self.accept()


class EnvironmentDialog(QDialog):
    """环境变量管理对话框"""

    def __init__(self, env_data: dict = None, parent=None):
        super().__init__(parent)
        self.env_data = env_data or {"name": "", "variables": {}}
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("管理环境变量")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        name_layout = QHBoxLayout()
        name_layout.addWidget(StrongBodyLabel("环境名称:"))
        self.name_input = LineEdit()
        self.name_input.setText(self.env_data.get("name", ""))
        self.name_input.setPlaceholderText("如：开发环境、测试环境、生产环境")
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

        layout.addWidget(StrongBodyLabel("变量列表:"))
        self.var_table = TableWidget()
        self.var_table.setRowCount(0)
        self.var_table.setColumnCount(2)
        self.var_table.setHorizontalHeaderLabels(["变量名", "变量值"])
        self.var_table.horizontalHeader().setStretchLastSection(True)
        self.var_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.var_table.setColumnWidth(0, 200)
        self.var_table.verticalHeader().setVisible(False)
        layout.addWidget(self.var_table)

        for k, v in self.env_data.get("variables", {}).items():
            row = self.var_table.rowCount()
            self.var_table.insertRow(row)
            self.var_table.setItem(row, 0, QTableWidgetItem(k))
            self.var_table.setItem(row, 1, QTableWidgetItem(str(v)))

        add_btn = PushButton("添加变量")
        add_btn.clicked.connect(self._add_var_row)
        layout.addWidget(add_btn)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = PushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        save_btn = PrimaryPushButton("保存")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _add_var_row(self):
        row = self.var_table.rowCount()
        self.var_table.insertRow(row)
        self.var_table.setItem(row, 0, QTableWidgetItem(""))
        self.var_table.setItem(row, 1, QTableWidgetItem(""))

    def _save(self):
        self.name_input.setFocus()
        QApplication.processEvents()

        name = self.name_input.text().strip()
        if not name:
            InfoBar.warning("提示", "请输入环境名称", parent=self, duration=2000)
            return

        variables = {}
        for row in range(self.var_table.rowCount()):
            key_item = self.var_table.item(row, 0)
            val_item = self.var_table.item(row, 1)
            if key_item and key_item.text().strip():
                variables[key_item.text().strip()] = val_item.text() if val_item else ""

        self.env_data = {"name": name, "variables": variables}
        self.accept()


class CollectionPickerDialog(QDialog):
    """树形集合选择对话框"""

    def __init__(self, collections: list, parent=None):
        super().__init__(parent)
        self.collections = collections
        self.selected_collection_id = None
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("选择目标集合")
        self.setMinimumSize(400, 450)
        self.setStyleSheet("font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        layout.addWidget(StrongBodyLabel("选择保存位置:"))

        self.tree = FluentTreeWidget()
        self.tree.setHeaderLabel("集合")
        self.tree.itemClicked.connect(self._on_item_clicked)

        children_map = {}
        root_collections = []
        for coll in self.collections:
            parent_id = coll.get("parent_id")
            if parent_id:
                children_map.setdefault(parent_id, []).append(coll)
            else:
                root_collections.append(coll)

        def add_coll_item(parent_item, coll):
            item = QTreeWidgetItem([f"📁 {coll['name']}"])
            item.setData(0, Qt.UserRole, coll)
            item.setExpanded(True)
            for child in children_map.get(coll["id"], []):
                add_coll_item(item, child)
            if parent_item:
                parent_item.addChild(item)
            else:
                self.tree.addTopLevelItem(item)

        for coll in root_collections:
            add_coll_item(None, coll)

        layout.addWidget(self.tree)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = PushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        ok_btn = PrimaryPushButton("确定")
        ok_btn.clicked.connect(self._on_accept)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

        self._selected_item = None

    def _on_item_clicked(self, item, column):
        self._selected_item = item

    def _on_accept(self):
        if self._selected_item:
            coll = self._selected_item.data(0, Qt.UserRole)
            if coll:
                self.selected_collection_id = coll["id"]
                self.accept()
                return
        InfoBar.warning("提示", "请选择一个集合", parent=self, duration=2000)
