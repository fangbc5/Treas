"""HTTP 客户端 - 侧边栏组件"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QAction,
    QTreeWidgetItem,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor

from qfluentwidgets import (
    ToolButton, InfoBar, TabWidget, FluentIcon, RoundMenu,
)

from constants import METHOD_COLORS
from widgets import FluentTreeWidget


class Sidebar(QWidget):
    """左侧边栏：集合 + 历史"""

    tab_changed = pyqtSignal(str)
    request_selected = pyqtSignal(dict)
    collection_action = pyqtSignal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = TabWidget()

        # --- 集合 Tab ---
        coll_widget = QWidget()
        coll_layout = QVBoxLayout(coll_widget)
        coll_layout.setContentsMargins(4, 4, 4, 4)
        coll_layout.setSpacing(4)

        coll_toolbar = QHBoxLayout()
        add_coll_btn = ToolButton(FluentIcon.FOLDER_ADD)
        add_coll_btn.setToolTip("新建集合")
        add_coll_btn.clicked.connect(lambda: self.collection_action.emit("add_collection", None))
        coll_toolbar.addWidget(add_coll_btn)

        add_req_btn = ToolButton(FluentIcon.ADD)
        add_req_btn.setToolTip("新建请求")
        add_req_btn.clicked.connect(lambda: self.collection_action.emit("add_request", None))
        coll_toolbar.addWidget(add_req_btn)

        coll_toolbar.addStretch()
        coll_layout.addLayout(coll_toolbar)

        self.collection_tree = FluentTreeWidget()
        self.collection_tree.setHeaderLabel("请求集合")
        self.collection_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.collection_tree.customContextMenuRequested.connect(self._on_collection_menu)
        self.collection_tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        coll_layout.addWidget(self.collection_tree)

        self.tabs.addTab(coll_widget, "📁 集合")

        # --- 历史 Tab ---
        hist_widget = QWidget()
        hist_layout = QVBoxLayout(hist_widget)
        hist_layout.setContentsMargins(4, 4, 4, 4)
        hist_layout.setSpacing(4)

        hist_toolbar = QHBoxLayout()
        clear_hist_btn = ToolButton(FluentIcon.DELETE)
        clear_hist_btn.setToolTip("清空历史")
        clear_hist_btn.clicked.connect(lambda: self.collection_action.emit("clear_history", None))
        hist_toolbar.addWidget(clear_hist_btn)
        hist_toolbar.addStretch()
        hist_layout.addLayout(hist_toolbar)

        self.history_tree = FluentTreeWidget()
        self.history_tree.setHeaderLabel("请求历史")
        self.history_tree.itemDoubleClicked.connect(self._on_history_double_clicked)
        self.history_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.history_tree.customContextMenuRequested.connect(self._on_history_menu)
        hist_layout.addWidget(self.history_tree)

        self.tabs.addTab(hist_widget, "🕐 历史")

        layout.addWidget(self.tabs)

    def _on_item_double_clicked(self, item, column):
        data = item.data(0, Qt.UserRole)
        if data and data.get("type") == "request":
            self.request_selected.emit(data)

    def _on_history_double_clicked(self, item, column):
        data = item.data(0, Qt.UserRole)
        if data:
            self.request_selected.emit(data)

    def get_selected_collection_id(self):
        item = self.collection_tree.currentItem()
        if not item:
            return None
        data = item.data(0, Qt.UserRole)
        if not data:
            return None
        if data.get("type") == "collection":
            return data.get("id")
        elif data.get("type") == "request":
            return data.get("collection_id")
        return None

    def _on_collection_menu(self, pos):
        item = self.collection_tree.itemAt(pos)
        menu = RoundMenu(parent=self)

        if item:
            data = item.data(0, Qt.UserRole)
            if data and data.get("type") == "collection":
                add_sub = QAction("📁 新建子集合", self)
                menu.addAction(add_sub)
                add_sub.triggered.connect(lambda: self.collection_action.emit("add_sub_collection", data))
                rename = QAction("✏️ 重命名", self)
                menu.addAction(rename)
                rename.triggered.connect(lambda: self.collection_action.emit("rename_collection", data))
                delete = QAction("🗑️ 删除集合", self)
                menu.addAction(delete)
                delete.triggered.connect(lambda: self.collection_action.emit("delete_collection", data))
                export_coll = QAction("📤 导出集合", self)
                menu.addAction(export_coll)
                export_coll.triggered.connect(lambda: self.collection_action.emit("export_collection", data))
            elif data and data.get("type") == "request":
                rename = QAction("✏️ 重命名", self)
                menu.addAction(rename)
                rename.triggered.connect(lambda: self.collection_action.emit("rename_request", data))
                delete = QAction("🗑️ 删除请求", self)
                menu.addAction(delete)
                delete.triggered.connect(lambda: self.collection_action.emit("delete_request", data))
                export_req = QAction("📤 导出请求", self)
                menu.addAction(export_req)
                export_req.triggered.connect(lambda: self.collection_action.emit("export_request", data))

        if menu.actions():
            menu.exec_(self.collection_tree.mapToGlobal(pos))

    def _on_history_menu(self, pos):
        item = self.history_tree.itemAt(pos)
        menu = RoundMenu(parent=self)

        if item:
            save = QAction("💾 保存到集合", self)
            menu.addAction(save)
            data = item.data(0, Qt.UserRole)
            save.triggered.connect(lambda: self.collection_action.emit("save_history_to_collection", data))

        if menu.actions():
            menu.exec_(self.history_tree.mapToGlobal(pos))

    def load_collections(self, collections: list, requests: list):
        self.collection_tree.clear()

        children_map = {}
        root_collections = []
        for coll in collections:
            parent_id = coll.get("parent_id")
            if parent_id:
                children_map.setdefault(parent_id, []).append(coll)
            else:
                root_collections.append(coll)

        def add_collection_tree(parent_item, coll):
            coll_item = QTreeWidgetItem([f"📁 {coll['name']}"])
            coll_item.setData(0, Qt.UserRole, {"type": "collection", **coll})
            coll_item.setExpanded(True)

            for child_coll in children_map.get(coll["id"], []):
                add_collection_tree(coll_item, child_coll)

            for req in requests:
                if req.get("collection_id") == coll["id"]:
                    method = req.get("method", "GET")
                    color = METHOD_COLORS.get(method, "#333")
                    req_item = QTreeWidgetItem([f"[{method}] {req['name']}"])
                    req_item.setData(0, Qt.UserRole, {"type": "request", **req})
                    req_item.setForeground(0, QColor(color))
                    coll_item.addChild(req_item)

            if parent_item:
                parent_item.addChild(coll_item)
            else:
                self.collection_tree.addTopLevelItem(coll_item)

        for coll in root_collections:
            add_collection_tree(None, coll)

    def add_history_item(self, entry: dict):
        method = entry.get("method", "GET")
        url = entry.get("url", "")
        status = entry.get("status_code", 0)
        color = METHOD_COLORS.get(method, "#333")

        short_url = url[:60] + "..." if len(url) > 60 else url
        display = f"[{method}] {short_url}"

        if status:
            display += f"  ({status})"

        item = QTreeWidgetItem([display])
        item.setData(0, Qt.UserRole, entry)
        item.setForeground(0, QColor(color))
        item.setToolTip(0, f"{method} {url}\n状态码: {status}\n时间: {entry.get('created_at', '')}")

        self.history_tree.insertTopLevelItem(0, item)

        while self.history_tree.topLevelItemCount() > 200:
            self.history_tree.takeTopLevelItem(self.history_tree.topLevelItemCount() - 1)

    def clear_history(self):
        self.history_tree.clear()