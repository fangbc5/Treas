"""HTTP 客户端 - 主插件组件"""

import sys
import os

# 确保插件目录在 sys.path 中（动态加载时插件目录默认不在搜索路径）
_PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
if _PLUGIN_DIR not in sys.path:
    sys.path.insert(0, _PLUGIN_DIR)

import json
import time
import re

from PyQt5.QtWidgets import (
    QWidget, QTextEdit, QHeaderView, QSplitter,
    QTreeWidgetItem, QTableWidgetItem,
    QDialog, QFormLayout, QInputDialog, QMessageBox, QApplication,
    QAbstractItemView, QVBoxLayout, QHBoxLayout, QAction, QSizePolicy,
    QFileDialog,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QKeySequence
from PyQt5.QtNetwork import QNetworkInterface

from qfluentwidgets import (
    PushButton, PrimaryPushButton, LineEdit, StrongBodyLabel, CaptionLabel,
    InfoBar, InfoBarPosition, ComboBox, TextEdit, TabWidget, TableWidget,
    FluentIcon, RoundMenu, ToolButton, CardWidget, HeaderCardWidget,
)

from src.core.plugin_base import PluginBase
from request_engine import HttpRequest, HttpResponse, RequestEngine
from curl_parser import parse_curl
from export_import import (
    export_to_postman_collection, export_single_request_to_postman,
    import_from_postman_collection,
)
from constants import *
from widgets import KeyValueTable, AuthPanel, BodyEditor
from sidebar import Sidebar
from dialogs import CurlImportDialog, EnvironmentDialog, CollectionPickerDialog

class HttpClientWidget(PluginBase):
    """HTTP 客户端插件"""

    plugin_id = "http_client"
    plugin_name = "HTTP 客户端"
    plugin_version = "1.0.0"
    plugin_description = "强大的 HTTP 接口测试工具，支持请求集合、环境变量、cURL导入"
    plugin_icon = "GLOBE"

    # 信号：用于从后台线程安全地更新 UI
    _response_received = pyqtSignal(object, object)  # (request, response)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._engine = RequestEngine()
        self._current_response = None
        self._is_sending = False
        self._current_request_id = None  # 当前编辑的已保存请求 ID
        self._current_collection_id = None  # 当前编辑的请求所属集合 ID
        self._current_snapshot = None  # 当前请求的基准快照（用于脏数据检测）
        self._init_ui()
        # 连接信号到 UI 更新槽函数
        self._response_received.connect(self._handle_response)
        # 延迟加载 DB 数据（_db_config 在 __init__ 之后由 PluginManager 注入）
        QTimer.singleShot(0, self._load_initial_data)

    def _init_ui(self):
        self.setStyleSheet(GLOBAL_STYLE + "background-color: #f0f0f0;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 使用 QSplitter 分割：左侧边栏 + 右侧内容
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)

        # ===== 左侧边栏 =====
        self._sidebar = Sidebar()
        self._sidebar.setMinimumWidth(180)
        self._sidebar.setMaximumWidth(360)
        self._sidebar.request_selected.connect(self._on_request_selected)
        self._sidebar.collection_action.connect(self._on_collection_action)
        splitter.addWidget(self._sidebar)

        # ===== 右侧面板 =====
        right_panel = QWidget()
        right_panel.setMinimumWidth(400)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # --- 请求栏 ---
        request_bar = QWidget()
        request_bar.setObjectName("requestBar")
        request_bar.setStyleSheet(REQUEST_BAR_STYLE + "padding: 8px 16px;")
        bar_layout = QHBoxLayout(request_bar)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar_layout.setSpacing(8)

        # 方法选择
        self._method_combo = ComboBox()
        self._method_combo.addItems(HTTP_METHODS)
        self._method_combo.setFixedWidth(100)
        self._method_combo.currentIndexChanged.connect(self._on_method_changed)
        bar_layout.addWidget(self._method_combo)

        # URL 输入
        self._url_input = LineEdit()
        self._url_input.setPlaceholderText("输入请求 URL，如 https://api.example.com/users")
        self._url_input.setStyleSheet("LineEdit { font-size: 14px; padding: 8px; }")
        self._url_input.returnPressed.connect(self._send_request)
        bar_layout.addWidget(self._url_input, 1)

        # 发送按钮
        self._send_btn = PrimaryPushButton("发送")
        self._send_btn.setFixedWidth(100)
        self._send_btn.setFixedHeight(36)
        self._send_btn.clicked.connect(self._send_request)
        bar_layout.addWidget(self._send_btn)

        # 保存按钮
        save_btn = ToolButton(FluentIcon.SAVE)
        save_btn.setToolTip("保存请求")
        save_btn.clicked.connect(lambda: self._on_collection_action("save_request", None))
        bar_layout.addWidget(save_btn)

        right_layout.addWidget(request_bar)

        # --- 请求/响应分割 ---
        req_resp_splitter = QSplitter(Qt.Vertical)
        req_resp_splitter.setHandleWidth(2)

        # --- 请求配置区 ---
        request_config = QWidget()
        request_config.setStyleSheet("background-color: white;")
        req_config_layout = QVBoxLayout(request_config)
        req_config_layout.setContentsMargins(0, 0, 0, 0)
        req_config_layout.setSpacing(0)

        # 请求配置 Tab
        self._req_tabs = TabWidget()

        # Params Tab
        self._params_table = KeyValueTable()
        self._req_tabs.addTab(self._params_table, "Params")

        # Headers Tab
        self._headers_table = KeyValueTable()
        self._req_tabs.addTab(self._headers_table, "Headers")

        # Body Tab
        self._body_editor = BodyEditor()
        self._req_tabs.addTab(self._body_editor, "Body")

        # Auth Tab
        self._auth_panel = AuthPanel()
        self._req_tabs.addTab(self._auth_panel, "Auth")

        req_config_layout.addWidget(self._req_tabs)
        request_config.setMinimumHeight(150)
        req_resp_splitter.addWidget(request_config)

        # --- 响应查看器 ---
        response_panel = QWidget()
        response_panel.setStyleSheet("background-color: white;")
        resp_layout = QVBoxLayout(response_panel)
        resp_layout.setContentsMargins(0, 0, 0, 0)
        resp_layout.setSpacing(0)

        # 状态栏
        self._status_bar = QWidget()
        self._status_bar.setFixedHeight(36)
        self._status_bar.setStyleSheet("background-color: #fafafa; border-top: 1px solid #e0e0e0;")
        status_layout = QHBoxLayout(self._status_bar)
        status_layout.setContentsMargins(16, 4, 16, 4)
        status_layout.setSpacing(16)

        self._status_label = CaptionLabel("等待请求...")
        self._status_label.setStyleSheet("font-size: 13px;")
        status_layout.addWidget(self._status_label)

        self._time_label = CaptionLabel("")
        status_layout.addWidget(self._time_label)

        self._size_label = CaptionLabel("")
        status_layout.addWidget(self._size_label)

        status_layout.addStretch()
        resp_layout.addWidget(self._status_bar)

        # 响应 Tab
        self._resp_tabs = TabWidget()

        # Body Tab（使用原生 QTextEdit 以支持自定义深色样式）
        self._resp_body = QTextEdit()
        self._resp_body.setReadOnly(True)
        self._resp_body.setLineWrapMode(QTextEdit.WidgetWidth)
        # 忽略水平 sizeHint，防止响应内容撑大右侧面板
        self._resp_body.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        self._resp_body.setStyleSheet(RESPONSE_BODY_STYLE)
        self._resp_tabs.addTab(self._resp_body, "Body")

        # Headers Tab
        self._resp_headers_table = TableWidget()
        self._resp_headers_table.setRowCount(0)
        self._resp_headers_table.setColumnCount(2)
        self._resp_headers_table.setHorizontalHeaderLabels(["Header", "Value"])
        self._resp_headers_table.horizontalHeader().setStretchLastSection(True)
        self._resp_headers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self._resp_headers_table.setColumnWidth(0, 250)
        self._resp_headers_table.verticalHeader().setVisible(False)
        self._resp_tabs.addTab(self._resp_headers_table, "Headers")

        resp_layout.addWidget(self._resp_tabs)
        req_resp_splitter.addWidget(response_panel)

        # 设置分割比例（禁止完全折叠，防止请求参数区被压没）
        req_resp_splitter.setChildrenCollapsible(False)
        req_resp_splitter.setStretchFactor(0, 1)
        req_resp_splitter.setStretchFactor(1, 1)
        req_resp_splitter.setSizes([300, 400])

        right_layout.addWidget(req_resp_splitter, 1)

        # --- 底部工具栏 ---
        toolbar = QWidget()
        toolbar.setFixedHeight(40)
        toolbar.setStyleSheet("background-color: white; border-top: 1px solid #e0e0e0;")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(16, 4, 16, 4)

        # 环境选择
        toolbar_layout.addWidget(CaptionLabel("环境:"))
        self._env_combo = ComboBox()
        self._env_combo.setFixedWidth(150)
        self._env_combo.addItem("无")
        self._env_combo.currentIndexChanged.connect(self._on_env_changed)
        toolbar_layout.addWidget(self._env_combo)

        env_manage_btn = ToolButton(FluentIcon.SETTING)
        env_manage_btn.setToolTip("管理环境变量")
        env_manage_btn.clicked.connect(self._manage_environments)
        toolbar_layout.addWidget(env_manage_btn)

        toolbar_layout.addStretch()

        # 导入 cURL
        curl_btn = PushButton("导入 cURL")
        curl_btn.setFixedHeight(28)
        curl_btn.clicked.connect(self._import_curl)
        toolbar_layout.addWidget(curl_btn)

        # 生成代码
        code_btn = PushButton("生成代码")
        code_btn.setFixedHeight(28)
        code_btn.clicked.connect(self._generate_code)
        toolbar_layout.addWidget(code_btn)

        # 导出全部
        export_all_btn = PushButton("📤 导出全部")
        export_all_btn.setFixedHeight(28)
        export_all_btn.clicked.connect(self._export_all)
        toolbar_layout.addWidget(export_all_btn)

        # 导入
        import_btn = PushButton("📥 导入")
        import_btn.setFixedHeight(28)
        import_btn.clicked.connect(self._import_collection)
        toolbar_layout.addWidget(import_btn)

        right_layout.addWidget(toolbar)

        splitter.addWidget(right_panel)
        splitter.setChildrenCollapsible(False)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 1140])

        main_layout.addWidget(splitter)

        # 初始化方法颜色
        self._on_method_changed(0)

    # ========== 公共工具方法 ==========

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """校验 URL 格式是否合法"""
        if not url:
            return False
        pattern = re.compile(
            r'^https?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return bool(pattern.match(url))

    # ========== 请求构建 ==========

    def _build_request(self) -> HttpRequest:
        """从 UI 构建请求对象"""
        req = HttpRequest()
        req.method = self._method_combo.currentText()
        req.url = self._url_input.text().strip()
        req.headers = self._headers_table.get_data()
        req.params = self._params_table.get_data()

        body_type, body_content = self._body_editor.get_data()
        req.body_type = body_type
        req.body_content = body_content

        auth_data = self._auth_panel.get_data()
        req.auth_type = auth_data.get("type", "none")
        req.auth_config = auth_data

        return req

    def _load_request(self, data: dict):
        """将请求数据加载到 UI"""
        self._method_combo.setCurrentText(data.get("method", "GET"))
        self._url_input.setText(data.get("url", ""))

        # 兼容处理：DB 中可能是 JSON 字符串，也可能是已解析的对象
        params = data.get("params", [])
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except (json.JSONDecodeError, TypeError):
                params = []
        headers = data.get("headers", [])
        if isinstance(headers, str):
            try:
                headers = json.loads(headers)
            except (json.JSONDecodeError, TypeError):
                headers = []

        self._params_table.set_data(params)
        self._headers_table.set_data(headers)

        self._body_editor.set_data(
            data.get("body_type", "none"),
            data.get("body_content", ""),
        )

        auth_type = data.get("auth_type", "none")
        auth_config = data.get("auth_config", {})
        if isinstance(auth_config, str):
            try:
                auth_config = json.loads(auth_config)
            except (json.JSONDecodeError, TypeError):
                auth_config = {}
        if auth_type != "none":
            auth_config["type"] = auth_type
            self._auth_panel.set_data(auth_config)
        else:
            self._auth_panel.set_data({"type": "none"})

    def _on_method_changed(self, index):
        method = self._method_combo.currentText()
        color = METHOD_COLORS.get(method, "#333")
        self._method_combo.setStyleSheet(f"""
            ComboBox {{
                color: {color};
                font-weight: bold;
                font-size: 14px;
                padding: 4px 8px;
            }}
        """)

    # ========== 发送请求 ==========

    def _send_request(self):
        if self._is_sending:
            # 正在请求中 → 取消：立即恢复 UI
            self._is_sending = False
            self._send_btn.setText("发送")
            self._status_label.setText("⚠️ 请求已取消")
            self._status_label.setStyleSheet("color: #e67e22; font-size: 13px;")
            self._engine.cancel()
            return

        request = self._build_request()
        if not request.url:
            InfoBar.warning("提示", "请输入 URL", parent=self, duration=2000)
            return

        # URL 格式校验
        if not self.is_valid_url(request.url):
            InfoBar.warning(
                "URL 格式错误",
                "请输入有效的 URL，例如：https://api.example.com/users",
                parent=self, duration=3000)
            return

        self._is_sending = True
        self._send_btn.setText("  取消  ")
        self._status_label.setText("⏳ 请求发送中...")
        self._resp_body.setPlainText("")

        def on_response(response):
            # 通过信号在主线程安全更新 UI
            self._response_received.emit(request, response)

        self._engine.execute(request, on_response)

    def _handle_response(self, request: HttpRequest, response: HttpResponse):
        # 如果用户已经手动取消了，不覆盖 UI 状态
        if not self._is_sending and response.error == "请求已取消":
            return
        self._is_sending = False
        self._send_btn.setText("发送")
        self._send_btn.setEnabled(True)
        self._current_response = response

        if response.error:
            self._status_label.setText(f"❌ {response.error}")
            self._status_label.setStyleSheet("color: #e74c3c; font-size: 13px;")
            self._time_label.setText("")
            self._size_label.setText("")
            self._resp_body.setPlainText(response.error)
            return

        # 状态码
        status_color = response.status_color
        self._status_label.setText(f"✅ {response.status_code} {response.reason}")
        self._status_label.setStyleSheet(f"color: {status_color}; font-size: 13px; font-weight: bold;")
        self._time_label.setText(f"⏱ {response.elapsed_ms:.0f}ms")
        self._size_label.setText(f"📦 {response.formatted_size}")

        # 响应体
        body = response.body
        if body:
            formatted = RequestEngine.format_json(body)
            self._resp_body.setPlainText(formatted)
        else:
            self._resp_body.setPlainText("(空响应)")

        # 响应头
        self._resp_headers_table.setRowCount(0)
        for key, value in response.headers.items():
            row = self._resp_headers_table.rowCount()
            self._resp_headers_table.insertRow(row)
            self._resp_headers_table.setItem(row, 0, QTableWidgetItem(key))
            self._resp_headers_table.setItem(row, 1, QTableWidgetItem(value))

        # 切换到 Body tab
        self._resp_tabs.setCurrentIndex(0)

        # 保存到历史
        self._save_to_history(request, response)

    # ========== 历史记录 ==========

    def _save_to_history(self, request: HttpRequest, response: HttpResponse):
        db = self.get_db()
        try:
            db.execute(
                """INSERT INTO request_history
                   (method, url, headers, params, body_type, body_content,
                    auth_type, auth_config, status_code, response_time,
                    response_size, response_headers, response_body)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    request.method,
                    request.url,
                    json.dumps(request.headers, ensure_ascii=False),
                    json.dumps(request.params, ensure_ascii=False),
                    request.body_type,
                    request.body_content,
                    request.auth_type,
                    json.dumps(request.auth_config, ensure_ascii=False),
                    response.status_code,
                    int(response.elapsed_ms),
                    response.size_bytes,
                    json.dumps(response.headers, ensure_ascii=False),
                    response.body,
                ),
            )
            db.commit()

            # 添加到侧边栏
            self._sidebar.add_history_item({
                "method": request.method,
                "url": request.url,
                "headers": request.headers,
                "params": request.params,
                "body_type": request.body_type,
                "body_content": request.body_content,
                "auth_type": request.auth_type,
                "auth_config": request.auth_config,
                "status_code": response.status_code,
                "response_time": int(response.elapsed_ms),
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            })
        except Exception as e:
            print(f"[HttpClient] 保存历史失败: {e}")
        finally:
            db.close()

    def _load_history(self):
        db = self.get_db()
        try:
            rows = db.execute(
                "SELECT * FROM request_history ORDER BY created_at DESC LIMIT 100"
            ).fetchall()
            for row in reversed(rows):
                entry = dict(row)
                self._sidebar.add_history_item(entry)
        except Exception as e:
            print(f"[HttpClient] 加载历史失败: {e}")
        finally:
            db.close()

    # ========== 集合管理 ==========

    def _load_collections(self):
        db = self.get_db()
        try:
            collections = [dict(r) for r in db.execute(
                "SELECT * FROM collections ORDER BY sort_order, created_at"
            ).fetchall()]
            requests = [dict(r) for r in db.execute(
                "SELECT * FROM saved_requests ORDER BY sort_order, created_at"
            ).fetchall()]
            self._sidebar.load_collections(collections, requests)
        except Exception as e:
            print(f"[HttpClient] 加载集合失败: {e}")
        finally:
            db.close()

    def _capture_snapshot(self) -> str:
        """捕获当前编辑器状态作为快照（用于脏数据对比）"""
        request = self._build_request()
        return json.dumps({
            "method": request.method,
            "url": request.url,
            "headers": request.headers,
            "params": request.params,
            "body_type": request.body_type,
            "body_content": request.body_content,
            "auth_type": request.auth_type,
            "auth_config": request.auth_config,
        }, sort_keys=True, ensure_ascii=False)

    def _mark_saved(self):
        """加载/保存请求后记录基准快照"""
        self._current_snapshot = self._capture_snapshot()

    def _is_dirty(self) -> bool:
        """检测当前编辑是否相对于上次保存/加载有改动"""
        if self._current_snapshot is None:
            return False
        return self._capture_snapshot() != self._current_snapshot

    def _check_save_dirty(self) -> bool:
        """如果有未保存改动，弹窗询问。返回 True 表示可以继续（已保存/丢弃），False 表示用户取消"""
        if not self._is_dirty():
            return True
        reply = QMessageBox.question(
            self, "未保存的修改",
            "当前请求有未保存的修改，是否保存？",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            self._save_current_request()
            return True
        elif reply == QMessageBox.No:
            return True  # 丢弃修改
        return False  # 取消

    def _on_request_selected(self, data: dict):
        """侧边栏选中请求"""
        if data.get("type") == "request":
            # 切换前检查脏数据
            if not self._check_save_dirty():
                return  # 用户取消切换
            # 记录当前编辑的请求 ID，保存时直接更新
            self._current_request_id = data.get("id")
            self._current_collection_id = data.get("collection_id")
            self._load_request(data)
            self._mark_saved()

    def _on_collection_action(self, action: str, data):
        """侧边栏集合操作"""
        if action == "add_collection":
            name, ok = QInputDialog.getText(self, "新建集合", "集合名称:")
            if ok and name.strip():
                db = self.get_db()
                try:
                    # 选中集合时新建为子集合，否则新建为根集合
                    parent_id = self._sidebar.get_selected_collection_id()
                    db.execute(
                        "INSERT INTO collections (name, parent_id) VALUES (?, ?)",
                        (name.strip(), parent_id),
                    )
                    db.commit()
                finally:
                    db.close()
                self._load_collections()

        elif action == "add_sub_collection" and data:
            name, ok = QInputDialog.getText(self, "新建子集合", "子集合名称:")
            if ok and name.strip():
                db = self.get_db()
                try:
                    db.execute("INSERT INTO collections (name, parent_id) VALUES (?, ?)",
                               (name.strip(), data["id"]))
                    db.commit()
                finally:
                    db.close()
                self._load_collections()

        elif action == "add_request":
            self._new_request()

        elif action == "save_request":
            self._save_current_request()

        elif action == "delete_collection" and data:
            msg = MessageBox("确认删除",
                             f"确定要删除集合「{data.get('name', '')}」及其所有请求吗？",
                             self)
            msg.yesSignal.connect(lambda: self._do_delete_collection(data))
            msg.exec_()

        elif action == "rename_collection" and data:
            name, ok = QInputDialog.getText(
                self, "重命名集合", "新名称:", text=data.get("name", "")
            )
            if ok and name.strip():
                db = self.get_db()
                try:
                    db.execute("UPDATE collections SET name = ? WHERE id = ?", (name.strip(), data["id"]))
                    db.commit()
                finally:
                    db.close()
                self._load_collections()

        elif action == "delete_request" and data:
            db = self.get_db()
            try:
                db.execute("DELETE FROM saved_requests WHERE id = ?", (data["id"],))
                db.commit()
            finally:
                db.close()
            self._load_collections()

        elif action == "rename_request" and data:
            name, ok = QInputDialog.getText(
                self, "重命名请求", "新名称:", text=data.get("name", "")
            )
            if ok and name.strip():
                db = self.get_db()
                try:
                    db.execute("UPDATE saved_requests SET name = ? WHERE id = ?", (name.strip(), data["id"]))
                    db.commit()
                finally:
                    db.close()
                self._load_collections()

        elif action == "clear_history":
            msg = MessageBox("确认", "确定要清空所有请求历史吗？", self)
            msg.yesSignal.connect(self._do_clear_history)
            msg.exec_()

        elif action == "save_history_to_collection" and data:
            self._save_history_entry_to_collection(data)

        elif action == "export_collection" and data:
            self._export_collection(data)

        elif action == "export_request" and data:
            self._export_request(data)

    def _do_delete_collection(self, data):
        """执行删除集合（由 MessageBox 确认后调用）"""
        db = self.get_db()
        try:
            db.execute("DELETE FROM saved_requests WHERE collection_id = ?", (data["id"],))
            db.execute("DELETE FROM collections WHERE id = ?", (data["id"],))
            db.commit()
        finally:
            db.close()
        self._load_collections()

    def _do_clear_history(self):
        """执行清空历史（由 MessageBox 确认后调用）"""
        db = self.get_db()
        try:
            db.execute("DELETE FROM request_history")
            db.commit()
        finally:
            db.close()
        self._sidebar.clear_history()

    def _new_request(self):
        """新建一个空白临时请求（保留当前选中的集合作为默认归属）"""
        # 检查脏数据
        if not self._check_save_dirty():
            return  # 用户取消

        # 清空编辑器为默认值
        self._method_combo.setCurrentText("GET")
        self._url_input.setText("")
        self._params_table.set_data([])
        self._headers_table.set_data([])
        self._body_editor.set_data("none", "")
        self._auth_panel.set_data({"type": "none"})

        # 重置为临时请求状态
        self._current_request_id = None
        # 自动归集到当前选中的集合（如有）
        self._current_collection_id = self._sidebar.get_selected_collection_id()
        self._mark_saved()

        # 聚焦 URL 输入框，方便立即开始编辑
        self._url_input.setFocus()
        InfoBar.info("新建请求",
                     "已新建空白请求" + (
                         f"，保存时将归入当前选中集合"
                         if self._current_collection_id else "，保存时可选择集合"),
                     parent=self, duration=2000)

    def _save_current_request(self):
        """保存当前请求：已打开的请求直接更新，临时请求走新建流程"""
        request = self._build_request()

        # 保存前校验 URL
        if request.url and not self.is_valid_url(request.url):
            InfoBar.warning(
                "URL 格式错误",
                "请输入有效的 URL，例如：https://api.example.com/users",
                parent=self, duration=3000)
            return

        # === 已打开的已保存请求 → 直接更新 ===
        if self._current_request_id:
            db = self.get_db()
            try:
                db.execute(
                    """UPDATE saved_requests
                       SET method=?, url=?, headers=?, params=?,
                           body_type=?, body_content=?, auth_type=?, auth_config=?
                       WHERE id=?""",
                    (
                        request.method,
                        request.url,
                        json.dumps(request.headers, ensure_ascii=False),
                        json.dumps(request.params, ensure_ascii=False),
                        request.body_type,
                        request.body_content,
                        request.auth_type,
                        json.dumps(request.auth_config, ensure_ascii=False),
                        self._current_request_id,
                    ),
                )
                db.commit()
            except Exception as e:
                InfoBar.error("保存失败", str(e), parent=self, duration=3000)
                return
            finally:
                db.close()

            self._load_collections()
            InfoBar.success("已保存", "请求已更新",
                            parent=self, duration=2000, position=InfoBarPosition.TOP)
            return

        # === 临时请求 → 走新建流程 ===
        db = self.get_db()
        try:
            collections = [dict(r) for r in db.execute(
                "SELECT id, name, parent_id FROM collections ORDER BY sort_order, created_at"
            ).fetchall()]
        finally:
            db.close()

        if not collections:
            InfoBar.info("提示", "请先创建一个集合", parent=self, duration=2000)
            return

        picker = CollectionPickerDialog(collections, parent=self)
        if picker.exec_() != QDialog.Accepted:
            return
        coll_id = picker.selected_collection_id
        if not coll_id:
            return

        req_name, ok2 = QInputDialog.getText(
            self, "请求名称", "为请求命名:", text=self._url_input.text().strip()[:50]
        )
        if not ok2 or not req_name.strip():
            return

        db = self.get_db()
        try:
            cursor = db.execute(
                """INSERT INTO saved_requests
                   (collection_id, name, method, url, headers, params,
                    body_type, body_content, auth_type, auth_config)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    coll_id,
                    req_name.strip(),
                    request.method,
                    request.url,
                    json.dumps(request.headers, ensure_ascii=False),
                    json.dumps(request.params, ensure_ascii=False),
                    request.body_type,
                    request.body_content,
                    request.auth_type,
                    json.dumps(request.auth_config, ensure_ascii=False),
                ),
            )
            db.commit()
            # 记录新保存的请求 ID，后续保存直接更新
            self._current_request_id = cursor.lastrowid
            self._current_collection_id = coll_id
        finally:
            db.close()

        # 查找集合名称用于提示
        coll_name = next((c["name"] for c in collections if c["id"] == coll_id), "")
        self._load_collections()
        self._mark_saved()
        InfoBar.success("已保存", f"请求「{req_name.strip()}」已保存到「{coll_name}」",
                        parent=self, duration=2000, position=InfoBarPosition.TOP)

    def _save_history_entry_to_collection(self, data: dict):
        """将历史记录保存到集合"""
        db = self.get_db()
        try:
            collections = [dict(r) for r in db.execute(
                "SELECT id, name, parent_id FROM collections ORDER BY sort_order, created_at"
            ).fetchall()]
        finally:
            db.close()

        if not collections:
            InfoBar.info("提示", "请先创建一个集合", parent=self, duration=2000)
            return

        picker = CollectionPickerDialog(collections, parent=self)
        if picker.exec_() != QDialog.Accepted:
            return
        coll_id = picker.selected_collection_id
        if not coll_id:
            return

        req_name, ok2 = QInputDialog.getText(
            self, "请求名称", "为请求命名:", text=data.get("url", "")[:50]
        )
        if not ok2 or not req_name.strip():
            return

        db = self.get_db()
        try:
            db.execute(
                """INSERT INTO saved_requests
                   (collection_id, name, method, url, headers, params,
                    body_type, body_content, auth_type, auth_config)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    coll_id,
                    req_name.strip(),
                    data.get("method", "GET"),
                    data.get("url", ""),
                    json.dumps(data.get("headers", []), ensure_ascii=False),
                    json.dumps(data.get("params", []), ensure_ascii=False),
                    data.get("body_type", "none"),
                    data.get("body_content", ""),
                    data.get("auth_type", "none"),
                    json.dumps(data.get("auth_config", {}), ensure_ascii=False),
                ),
            )
            db.commit()
        finally:
            db.close()

        # 查找集合名称用于提示
        saved_coll_name = next((c["name"] for c in collections if c["id"] == coll_id), "")
        self._load_collections()
        InfoBar.success("已保存", f"请求「{req_name.strip()}」已保存到「{saved_coll_name}」",
                        parent=self, duration=2000)

    # ========== 环境变量 ==========

    def _load_environments(self):
        db = self.get_db()
        try:
            rows = db.execute("SELECT * FROM environments ORDER BY name").fetchall()
            self._env_combo.clear()
            self._env_combo.addItem("无")
            for row in rows:
                env = dict(row)
                self._env_combo.addItem(env["name"])
                if env.get("is_active"):
                    self._env_combo.setCurrentText(env["name"])
        except Exception as e:
            print(f"[HttpClient] 加载环境变量失败: {e}")
        finally:
            db.close()

    def _on_env_changed(self, index):
        if index <= 0:
            self._engine.set_variables({})
            return

        env_name = self._env_combo.currentText()
        db = self.get_db()
        try:
            row = db.execute(
                "SELECT variables FROM environments WHERE name = ?", (env_name,)
            ).fetchone()
            if row:
                variables = json.loads(row["variables"]) if row["variables"] else {}
                self._engine.set_variables(variables)

                # 更新数据库中的激活状态
                db.execute("UPDATE environments SET is_active = 0")
                db.execute("UPDATE environments SET is_active = 1 WHERE name = ?", (env_name,))
                db.commit()
        except Exception as e:
            print(f"[HttpClient] 切换环境失败: {e}")
        finally:
            db.close()

    def _manage_environments(self):
        menu = RoundMenu(parent=self)

        add_env = QAction("➕ 新建环境", self)
        menu.addAction(add_env)
        add_env.triggered.connect(self._add_environment)

        # 已有环境列表
        db = self.get_db()
        try:
            envs = [dict(r) for r in db.execute("SELECT * FROM environments ORDER BY name").fetchall()]
        finally:
            db.close()

        if envs:
            menu.addSeparator()
            for env in envs:
                submenu = RoundMenu(env['name'], self)
                menu.addMenu(submenu)
                edit_action = QAction("编辑", self)
                submenu.addAction(edit_action)
                edit_action.triggered.connect(lambda checked, e=env: self._edit_environment(e))
                delete_action = QAction("删除", self)
                submenu.addAction(delete_action)
                delete_action.triggered.connect(lambda checked, e=env: self._delete_environment(e))

        menu.exec_(self.mapToGlobal(
            self._env_combo.mapToParent(self._env_combo.rect().bottomLeft())
        ))

    def _add_environment(self):
        dialog = EnvironmentDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            db = self.get_db()
            try:
                db.execute(
                    "INSERT INTO environments (name, variables) VALUES (?, ?)",
                    (dialog.env_data["name"], json.dumps(dialog.env_data["variables"], ensure_ascii=False)),
                )
                db.commit()
            except Exception as e:
                InfoBar.error("错误", str(e), parent=self, duration=3000)
            finally:
                db.close()
            self._load_environments()

    def _edit_environment(self, env: dict):
        variables = json.loads(env.get("variables", "{}")) if env.get("variables") else {}
        dialog = EnvironmentDialog({"name": env["name"], "variables": variables}, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            db = self.get_db()
            try:
                old_name = env["name"]
                new_name = dialog.env_data["name"]
                db.execute(
                    "UPDATE environments SET name = ?, variables = ? WHERE name = ?",
                    (new_name, json.dumps(dialog.env_data["variables"], ensure_ascii=False), old_name),
                )
                db.commit()
            finally:
                db.close()
            self._load_environments()

    def _delete_environment(self, env: dict):
        msg = MessageBox("确认删除", f"确定要删除环境「{env['name']}」吗？", self)
        msg.yesSignal.connect(lambda: self._do_delete_environment(env))
        msg.exec_()

    def _do_delete_environment(self, env):
        """执行删除环境（由 MessageBox 确认后调用）"""
        db = self.get_db()
        try:
            db.execute("DELETE FROM environments WHERE id = ?", (env["id"],))
            db.commit()
        finally:
            db.close()
        self._load_environments()
        self._engine.set_variables({})

    # ========== 导入/导出 ==========

    def _export_collection(self, data):
        """导出单个集合（含子集合和请求）"""
        db = self.get_db()
        try:
            # 获取该集合及所有子集合
            coll_ids = self._get_collection_tree_ids(data["id"], db)
            collections = [dict(r) for r in db.execute(
                "SELECT * FROM collections WHERE id IN ({})".format(
                    ",".join("?" for _ in coll_ids)
                ), coll_ids
            ).fetchall()]
            requests = [dict(r) for r in db.execute(
                "SELECT * FROM saved_requests WHERE collection_id IN ({})".format(
                    ",".join("?" for _ in coll_ids)
                ), coll_ids
            ).fetchall()]
        finally:
            db.close()

        if not requests and len(collections) <= 1:
            InfoBar.info("提示", "该集合下没有请求可导出", parent=self, duration=2000)
            return

        pm_data = export_to_postman_collection(collections, requests)
        pm_data["info"]["name"] = data.get("name", "导出集合")

        self._save_json_file(pm_data, f"{data.get('name', 'collection')}.json")

    def _export_request(self, data):
        """导出单个请求"""
        pm_data = export_single_request_to_postman(data)
        pm_data["info"]["name"] = data.get("name", "导出请求")
        self._save_json_file(pm_data, f"{data.get('name', 'request')}.json")

    def _export_all(self):
        """导出全部集合 + 环境变量"""
        db = self.get_db()
        try:
            collections = [dict(r) for r in db.execute(
                "SELECT * FROM collections ORDER BY sort_order, created_at"
            ).fetchall()]
            requests = [dict(r) for r in db.execute(
                "SELECT * FROM saved_requests ORDER BY sort_order, created_at"
            ).fetchall()]
            environments = [dict(r) for r in db.execute(
                "SELECT * FROM environments ORDER BY name"
            ).fetchall()]
        finally:
            db.close()

        if not requests and not collections:
            InfoBar.info("提示", "没有数据可导出", parent=self, duration=2000)
            return

        pm_data = export_to_postman_collection(collections, requests, environments)
        self._save_json_file(pm_data, "treas_export.json")

    def _save_json_file(self, data, default_filename):
        """弹出文件保存对话框，写入 JSON 文件"""
        from PyQt5.QtWidgets import QFileDialog
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出文件", default_filename,
            "Postman Collection (*.json);;所有文件 (*)",
        )
        if not filepath:
            return
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            InfoBar.success("导出成功", f"已导出到 {os.path.basename(filepath)}",
                            parent=self, duration=3000, position=InfoBarPosition.TOP)
        except Exception as e:
            InfoBar.error("导出失败", str(e), parent=self, duration=3000)

    def _import_collection(self):
        """导入 Postman Collection 文件"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "导入文件", "",
            "Postman Collection (*.json);;所有文件 (*)",
        )
        if not filepath:
            return

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            InfoBar.error("读取失败", str(e), parent=self, duration=3000)
            return

        try:
            parsed = import_from_postman_collection(content)
        except Exception as e:
            InfoBar.error("解析失败", f"不支持的文件格式: {e}",
                            parent=self, duration=3000)
            return

        if not parsed["collections"] and not parsed["requests"]:
            InfoBar.warning("提示", "文件中没有找到有效的集合或请求",
                            parent=self, duration=2000)
            return

        # 导入到数据库
        db = self.get_db()
        try:
            # 名称 → ID 映射（用于建立父子关系和请求归属）
            name_to_id = {}

            # 导入集合
            for coll in parsed["collections"]:
                parent_name = coll.get("parent_name")
                parent_id = name_to_id.get(parent_name) if parent_name else None
                cursor = db.execute(
                    "INSERT INTO collections (name, parent_id, description) VALUES (?, ?, ?)",
                    (coll["name"], parent_id, coll.get("description", "")),
                )
                db.commit()
                name_to_id[coll["name"]] = cursor.lastrowid

            # 导入请求
            imported_count = 0
            for req in parsed["requests"]:
                coll_name = req.get("collection_name")
                coll_id = name_to_id.get(coll_name) if coll_name else None
                if not coll_id:
                    # 没有集合则创建一个默认集合
                    if "未导入集合" not in name_to_id:
                        cursor = db.execute(
                            "INSERT INTO collections (name) VALUES (?)", ("未导入集合",)
                        )
                        db.commit()
                        name_to_id["未导入集合"] = cursor.lastrowid
                    coll_id = name_to_id["未导入集合"]

                db.execute(
                    """INSERT INTO saved_requests
                       (collection_id, name, method, url, headers, params,
                        body_type, body_content, auth_type, auth_config)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        coll_id,
                        req["name"],
                        req.get("method", "GET"),
                        req.get("url", ""),
                        json.dumps(req.get("headers", []), ensure_ascii=False),
                        json.dumps(req.get("params", []), ensure_ascii=False),
                        req.get("body_type", "none"),
                        req.get("body_content", ""),
                        req.get("auth_type", "none"),
                        json.dumps(req.get("auth_config", {}), ensure_ascii=False),
                    ),
                )
                imported_count += 1

            # 导入环境变量
            for env in parsed["environments"]:
                try:
                    db.execute(
                        "INSERT INTO environments (name, variables) VALUES (?, ?)",
                        (env["name"], json.dumps(env["variables"], ensure_ascii=False)),
                    )
                except Exception:
                    pass  # 同名环境跳过

            db.commit()
        finally:
            db.close()

        # 刷新 UI
        self._load_collections()
        self._load_environments()

        total = len(parsed["collections"])
        InfoBar.success(
            "导入成功",
            f"已导入 {total} 个集合、{imported_count} 个请求"
            + (f"、{len(parsed['environments'])} 个环境" if parsed['environments'] else ""),
            parent=self, duration=3000, position=InfoBarPosition.TOP,
        )

    def _get_collection_tree_ids(self, coll_id, db):
        """获取集合及其所有子集合的 ID 列表"""
        ids = [coll_id]
        children = db.execute(
            "SELECT id FROM collections WHERE parent_id = ?", (coll_id,)
        ).fetchall()
        for child in children:
            ids.extend(self._get_collection_tree_ids(child[0], db))
        return ids

    # ========== cURL 导入 ==========

    def _import_curl(self):
        dialog = CurlImportDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted and dialog.parsed_data:
            data = dialog.parsed_data
            self._current_request_id = None  # cURL 导入是临时请求
            self._current_collection_id = None
            self._load_request(data)
            InfoBar.success("导入成功", "cURL 命令已解析并填入",
                            parent=self, duration=2000, position=InfoBarPosition.TOP)

    # ========== 代码生成 ==========

    def _generate_code(self):
        request = self._build_request()
        if not request.url:
            InfoBar.warning("提示", "请先输入 URL", parent=self, duration=2000)
            return

        menu = RoundMenu(parent=self)

        for lang in ["Python (requests)", "cURL", "JavaScript (fetch)"]:
            action = QAction(lang, self)
            menu.addAction(action)
            action.triggered.connect(lambda checked, l=lang: self._copy_code(l))

        menu.exec_(self.mapToGlobal(self.cursor().pos()))

    def _copy_code(self, lang_label: str):
        request = self._build_request()
        lang_map = {
            "Python (requests)": "python",
            "cURL": "curl",
            "JavaScript (fetch)": "fetch",
        }
        lang = lang_map.get(lang_label, "python")
        code = RequestEngine.generate_code(request, lang)

        if code:
            clipboard = QApplication.clipboard()
            clipboard.setText(code)
            InfoBar.success("已复制", f"{lang_label} 代码已复制到剪贴板",
                            parent=self, duration=2000, position=InfoBarPosition.TOP)
        else:
            InfoBar.warning("提示", "代码生成失败", parent=self, duration=2000)

    # ========== 初始化加载 ==========

    def _load_initial_data(self):
        """延迟加载 DB 数据（在 _db_config 被注入后调用）"""
        if not self._db_config:
            return
        try:
            self._migrate_db()
            self._load_collections()
            self._load_history()
            self._load_environments()
        except Exception as e:
            print(f"[HttpClient] 初始化数据加载失败: {e}")

    def _migrate_db(self):
        """数据库迁移：为已有数据库添加 parent_id 字段"""
        db = self.get_db()
        try:
            cols = [row[1] for row in db.execute("PRAGMA table_info(collections)").fetchall()]
            if "parent_id" not in cols:
                db.execute("ALTER TABLE collections ADD COLUMN parent_id INTEGER DEFAULT NULL")
                db.commit()
                print("[HttpClient] 数据库迁移: 已添加 parent_id 字段")
        except Exception as e:
            print(f"[HttpClient] 数据库迁移检查: {e}")
        finally:
            db.close()

    # ========== 生命周期 ==========

    def on_activate(self):
        super().on_activate()

    def on_deactivate(self):
        super().on_deactivate()