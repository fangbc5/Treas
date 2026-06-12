"""密码保险箱 - 主 UI"""

import sys
import os
import json

# 设置项目根目录到 sys.path
_project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton,
    QListWidget, QListWidgetItem, QComboBox,
    QCheckBox, QSlider, QDialog, QFormLayout,
    QGroupBox, QFrame, QSplitter, QMenu, QAction,
    QSizePolicy, QApplication,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QClipboard

from qfluentwidgets import (
    PushButton, PrimaryPushButton, LineEdit,
    StrongBodyLabel, CaptionLabel, SubtitleLabel,
    InfoBar, InfoBarPosition, FluentIcon,
    CardWidget, TransparentToolButton,
    setCustomStyleSheet,
)

from src.core.plugin_base import PluginBase

# 同目录模块
sys.path.insert(0, os.path.dirname(__file__))
from crypto_utils import (
    generate_salt, hash_password, encrypt_password,
    decrypt_password, verify_master_password,
)
from password_generator import generate_password, calculate_strength


# 分类定义
CATEGORIES = {
    "all": ("全部", FluentIcon.APPLICATION),
    "favorite": ("收藏", FluentIcon.HEART),
    "login": ("登录", FluentIcon.LINK),
    "bank": ("银行卡", FluentIcon.CERTIFICATE),
    "wifi": ("WiFi", FluentIcon.WIFI),
    "identity": ("身份", FluentIcon.PEOPLE),
    "credit_card": ("信用卡", FluentIcon.BOOK_SHELF),
    "note": ("安全笔记", FluentIcon.DOCUMENT),
}

# 分类对应的字段模板
CATEGORY_TEMPLATES = {
    "login": {"username": "用户名", "password": "密码", "url": "网址"},
    "bank": {"username": "卡号", "password": "密码", "url": "开户行"},
    "wifi": {"username": "网络名称(SSID)", "password": "密码", "url": ""},
    "identity": {"username": "证件号码", "password": "", "url": ""},
    "credit_card": {"username": "卡号", "password": "CVV", "url": "有效期"},
    "note": {"username": "", "password": "", "url": ""},
}


class MasterPasswordDialog(QDialog):
    """主密码设置/验证对话框"""

    def __init__(self, is_setup: bool, parent=None):
        super().__init__(parent)
        self.is_setup = is_setup
        self.master_password = None
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("设置主密码" if self.is_setup else "解锁保险箱")
        self.setFixedWidth(400)
        self.setFixedHeight(320 if self.is_setup else 260)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(32, 32, 32, 32)

        # 图标 + 标题
        title = SubtitleLabel("🔐 设置主密码" if self.is_setup else "🔐 解锁保险箱")
        layout.addWidget(title)

        desc = CaptionLabel(
            "请设置一个强主密码，它将用于加密你的所有密码。\n请务必记住，忘记后将无法恢复！"
            if self.is_setup
            else "请输入主密码以解锁保险箱"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # 密码输入
        self.pwd_input = LineEdit()
        self.pwd_input.setEchoMode(LineEdit.Password)
        self.pwd_input.setPlaceholderText("输入主密码")
        self.pwd_input.returnPressed.connect(self._on_confirm)
        layout.addWidget(self.pwd_input)

        # 确认密码（仅设置时）
        if self.is_setup:
            self.confirm_input = LineEdit()
            self.confirm_input.setEchoMode(LineEdit.Password)
            self.confirm_input.setPlaceholderText("再次确认主密码")
            self.confirm_input.returnPressed.connect(self._on_confirm)
            layout.addWidget(self.confirm_input)

            # 强度提示
            self.strength_label = CaptionLabel("")
            self.pwd_input.textChanged.connect(self._update_strength)
            layout.addWidget(self.strength_label)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = PushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        confirm_btn = PrimaryPushButton("确认")
        confirm_btn.clicked.connect(self._on_confirm)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(confirm_btn)
        layout.addLayout(btn_layout)

    def _update_strength(self, text):
        if not text:
            self.strength_label.setText("")
            return
        result = calculate_strength(text)
        self.strength_label.setText(f"密码强度: {result['label']}")
        self.strength_label.setStyleSheet(f"color: {result['color']};")

    def _on_confirm(self):
        pwd = self.pwd_input.text()
        if not pwd:
            return

        if self.is_setup:
            if len(pwd) < 6:
                InfoBar.warning("提示", "主密码至少6个字符", parent=self, duration=2000)
                return
            if hasattr(self, "confirm_input"):
                if pwd != self.confirm_input.text():
                    InfoBar.error("错误", "两次密码不一致", parent=self, duration=2000)
                    return
            self.master_password = pwd
        else:
            self.master_password = pwd

        self.accept()


class EntryEditDialog(QDialog):
    """条目编辑对话框"""

    def __init__(self, entry=None, master_password="", salt="", parent=None):
        super().__init__(parent)
        self.entry = entry or {}
        self.master_password = master_password
        self.salt = salt
        self.result_data = None
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("编辑条目" if self.entry.get("id") else "添加条目")
        self.setMinimumWidth(520)
        self.setMinimumHeight(400)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        # 分类选择
        cat_layout = QHBoxLayout()
        cat_label = StrongBodyLabel("分类:")
        self.cat_combo = QComboBox()
        self.cat_combo.setStyleSheet("""
            QComboBox {
                padding: 6px 12px;
                border: 1px solid #d0d0d0;
                border-radius: 6px;
                background: white;
                color: #333333;
                font-size: 13px;
            }
            QComboBox:hover {
                border-color: #1a73e8;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox QAbstractItemView {
                background: white;
                color: #333333;
                border: 1px solid #d0d0d0;
                selection-background-color: #e8f0fe;
                selection-color: #1a73e8;
                outline: none;
            }
        """)
        for key, (name, _) in CATEGORIES.items():
            if key not in ("all", "favorite"):
                self.cat_combo.addItem(name, key)
        # 设置当前分类
        current_cat = self.entry.get("category", "login")
        for i in range(self.cat_combo.count()):
            if self.cat_combo.itemData(i) == current_cat:
                self.cat_combo.setCurrentIndex(i)
                break
        cat_layout.addWidget(cat_label)
        cat_layout.addWidget(self.cat_combo, 1)
        layout.addLayout(cat_layout)

        # 标题
        title_layout = QHBoxLayout()
        title_label = StrongBodyLabel("标题:")
        self.title_input = LineEdit()
        self.title_input.setText(self.entry.get("title", ""))
        self.title_input.setPlaceholderText("例如：GitHub 账号")
        title_layout.addWidget(title_label)
        title_layout.addWidget(self.title_input, 1)
        layout.addLayout(title_layout)

        # 动态字段区
        layout.addWidget(StrongBodyLabel("详细信息:"))
        fields_widget = QWidget()
        self.fields_layout = QFormLayout(fields_widget)
        self.fields_layout.setContentsMargins(0, 4, 0, 0)
        self.fields_layout.setSpacing(8)
        self.fields_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        self.fields_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        template = CATEGORY_TEMPLATES.get(current_cat, {})
        # 用户名
        self.username_input = LineEdit()
        self.username_input.setFixedWidth(320)
        self.username_input.setText(self.entry.get("username", ""))
        self.fields_layout.addRow(self._get_field_label(template, "username", "用户名"), self.username_input)

        # 密码（带生成按钮）
        pwd_layout = QHBoxLayout()
        self.pwd_input = LineEdit()
        self.pwd_input.setFixedWidth(320)
        self.pwd_input.setEchoMode(LineEdit.Password)
        # 解密密码
        encrypted_pwd = self.entry.get("password_encrypted", "")
        if encrypted_pwd and self.master_password and self.salt:
            try:
                self.pwd_input.setText(decrypt_password(encrypted_pwd, self.master_password, self.salt))
            except Exception:
                self.pwd_input.setText("")

        self.pwd_toggle = TransparentToolButton(FluentIcon.VIEW)
        self.pwd_toggle.setFixedSize(32, 32)
        self.pwd_toggle.clicked.connect(self._toggle_password)

        gen_btn = TransparentToolButton(FluentIcon.SYNC)
        gen_btn.setFixedSize(32, 32)
        gen_btn.setToolTip("生成密码")
        gen_btn.clicked.connect(self._generate_and_fill)

        pwd_layout.addWidget(self.pwd_input, 1)
        pwd_layout.addWidget(self.pwd_toggle)
        pwd_layout.addWidget(gen_btn)
        self.fields_layout.addRow(self._get_field_label(template, "password", "密码"), pwd_layout)

        # URL/其他
        self.url_input = LineEdit()
        self.url_input.setFixedWidth(320)
        self.url_input.setText(self.entry.get("url", ""))
        self.fields_layout.addRow(self._get_field_label(template, "url", "网址"), self.url_input)

        layout.addWidget(fields_widget)

        # 备注
        layout.addWidget(StrongBodyLabel("备注:"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setFixedHeight(80)
        self.notes_edit.setPlaceholderText("可选备注信息...")
        self.notes_edit.setPlainText(self.entry.get("notes", ""))
        layout.addWidget(self.notes_edit)

        # 收藏
        self.fav_check = QCheckBox("添加到收藏")
        self.fav_check.setChecked(bool(self.entry.get("is_favorite", 0)))
        layout.addWidget(self.fav_check)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = PushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        save_btn = PrimaryPushButton("保存")
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    @staticmethod
    def _get_field_label(template, field, default):
        label = template.get(field, default) or default
        return StrongBodyLabel(label)

    def _toggle_password(self):
        if self.pwd_input.echoMode() == QLineEdit.Password:
            self.pwd_input.setEchoMode(LineEdit.Normal)
            self.pwd_toggle.setIcon(FluentIcon.HIDE)
        else:
            self.pwd_input.setEchoMode(LineEdit.Password)
            self.pwd_toggle.setIcon(FluentIcon.VIEW)

    def _generate_and_fill(self):
        pwd = generate_password(length=16)
        self.pwd_input.setText(pwd)
        self.pwd_input.setEchoMode(LineEdit.Normal)
        self.pwd_toggle.setIcon(FluentIcon.HIDE)

    def _on_save(self):
        title = self.title_input.text().strip()
        if not title:
            InfoBar.warning("提示", "请输入标题", parent=self, duration=2000)
            return

        pwd_text = self.pwd_input.text()
        encrypted = ""
        if pwd_text and self.master_password and self.salt:
            encrypted = encrypt_password(pwd_text, self.master_password, self.salt)

        self.result_data = {
            "category": self.cat_combo.currentData(),
            "title": title,
            "username": self.username_input.text().strip(),
            "password_encrypted": encrypted,
            "url": self.url_input.text().strip(),
            "notes": self.notes_edit.toPlainText().strip(),
            "is_favorite": 1 if self.fav_check.isChecked() else 0,
        }
        self.accept()


class PasswordVaultWidget(PluginBase):
    """密码保险箱插件"""

    plugin_id = "password_vault"
    plugin_name = "密码保险箱"
    plugin_version = "1.0.0"
    plugin_description = "本地加密存储账号密码，支持多种模板、密码生成器和安全审计"
    plugin_icon = "CERTIFICATE"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._master_password = ""
        self._salt = ""
        self._is_locked = True
        self._clipboard_timer = None
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("background-color: #fafafa;")

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        # 锁屏页面（默认显示）
        self._lock_page = self._create_lock_page()
        self._main_layout.addWidget(self._lock_page)

        # 主内容页面（解锁后显示）
        self._vault_page = self._create_vault_page()
        self._main_layout.addWidget(self._vault_page)
        self._vault_page.hide()

    def _create_lock_page(self):
        """创建锁屏页面"""
        page = QWidget()
        page.setStyleSheet("background-color: #f5f5f5;")
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)

        # 锁图标
        lock_icon = QLabel("🔐")
        lock_icon.setStyleSheet("font-size: 64px;")
        lock_icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(lock_icon)

        title = SubtitleLabel("密码保险箱已锁定")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        hint = CaptionLabel("所有密码均使用 AES-256 加密存储在本地")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

        unlock_btn = PrimaryPushButton("解锁")
        unlock_btn.setFixedWidth(200)
        unlock_btn.clicked.connect(self._on_unlock)
        layout.addWidget(unlock_btn, alignment=Qt.AlignCenter)

        return page

    def _create_vault_page(self):
        """创建主内容页面"""
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        # 顶部栏
        toolbar = QWidget()
        toolbar.setFixedHeight(48)
        toolbar.setStyleSheet("background-color: white;")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(16, 8, 16, 8)

        title = StrongBodyLabel("🔐 密码保险箱")
        title.setStyleSheet("font-size: 15px;")
        toolbar_layout.addWidget(title)

        toolbar_layout.addStretch()

        # 搜索框
        self._search_input = LineEdit()
        self._search_input.setPlaceholderText("🔍 搜索...")
        self._search_input.setFixedWidth(200)
        self._search_input.textChanged.connect(self._on_search)
        toolbar_layout.addWidget(self._search_input)

        # 添加按钮
        add_btn = PrimaryPushButton(FluentIcon.ADD, "添加")
        add_btn.clicked.connect(self._on_add_entry)
        toolbar_layout.addWidget(add_btn)

        # 锁定按钮
        lock_btn = PushButton("🔒 锁定")
        lock_btn.clicked.connect(self._lock)
        toolbar_layout.addWidget(lock_btn)

        page_layout.addWidget(toolbar)

        # 内容区：左侧分类 + 右侧条目列表
        content = QWidget()
        content.setStyleSheet("background-color: white;")
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # 左侧分类导航
        self._cat_list = QListWidget()
        self._cat_list.setFixedWidth(120)
        self._cat_list.setStyleSheet("""
            QListWidget {
                background: white;
                border: none;
                border-right: 1px solid #e0e0e0;
                font-size: 13px;
                outline: none;
            }
            QListWidget::item {
                padding: 10px 12px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected {
                background: #e8f0fe;
                color: #1a73e8;
            }
        """)
        for key, (name, _) in CATEGORIES.items():
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, key)
            self._cat_list.addItem(item)
        self._cat_list.setCurrentRow(0)
        self._cat_list.currentItemChanged.connect(self._on_category_changed)
        content_layout.addWidget(self._cat_list)

        # 右侧条目列表
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self._entries_list = QListWidget()
        self._entries_list.setStyleSheet("""
            QListWidget {
                background: white;
                border: none;
                font-size: 13px;
                outline: none;
            }
            QListWidget::item {
                padding: 12px 16px;
                border-bottom: 1px solid #f0f0f0;
                color: #333333;
            }
            QListWidget::item:selected {
                background: #e8f0fe;
                color: #1a73e8;
            }
        """)
        self._entries_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._entries_list.customContextMenuRequested.connect(self._on_entry_context_menu)
        self._entries_list.itemDoubleClicked.connect(self._on_edit_entry_item)
        right_layout.addWidget(self._entries_list)

        # 底部状态栏
        self._status_bar = QWidget()
        self._status_bar.setFixedHeight(32)
        self._status_bar.setStyleSheet("background: white;")
        status_layout = QHBoxLayout(self._status_bar)
        status_layout.setContentsMargins(16, 4, 16, 4)
        self._status_label = CaptionLabel("就绪")
        status_layout.addWidget(self._status_label)
        status_layout.addStretch()
        right_layout.addWidget(self._status_bar)

        content_layout.addWidget(right_panel, 1)

        page_layout.addWidget(content)
        return page

    # ========== 解锁/锁定逻辑 ==========

    def _on_unlock(self):
        """解锁保险箱"""
        db = self.get_db()
        try:
            row = db.execute("SELECT password_hash, salt FROM master_key WHERE id = 1").fetchone()
            if row:
                # 已有主密码 -> 验证
                stored_hash = row["password_hash"]
                self._salt = row["salt"]

                dialog = MasterPasswordDialog(is_setup=False, parent=self)
                if dialog.exec_() != QDialog.Accepted:
                    return

                if not verify_master_password(dialog.master_password, stored_hash, self._salt):
                    InfoBar.error("错误", "主密码错误", parent=self, duration=2000)
                    return

                self._master_password = dialog.master_password
            else:
                # 首次使用 -> 设置主密码
                dialog = MasterPasswordDialog(is_setup=True, parent=self)
                if dialog.exec_() != QDialog.Accepted:
                    return

                self._salt = generate_salt()
                self._master_password = dialog.master_password
                pwd_hash = hash_password(self._master_password, self._salt)

                db.execute(
                    "INSERT INTO master_key (id, password_hash, salt) VALUES (1, ?, ?)",
                    (pwd_hash, self._salt),
                )
                db.commit()

            self._is_locked = False
            self._lock_page.hide()
            self._vault_page.show()
            self._refresh_entries()

            InfoBar.success("成功", "保险箱已解锁", parent=self, duration=2000, position=InfoBarPosition.TOP)
        except ImportError as e:
            InfoBar.error("缺少依赖", str(e), parent=self, duration=5000, position=InfoBarPosition.TOP)
        finally:
            db.close()

    def _lock(self):
        """锁定保险箱"""
        self._master_password = ""
        self._salt = ""
        self._is_locked = True
        self._vault_page.hide()
        self._lock_page.show()

    # ========== 条目管理 ==========

    def _refresh_entries(self):
        """刷新条目列表"""
        if self._is_locked:
            return

        db = self.get_db()
        try:
            current_cat = self._cat_list.currentItem()
            cat_key = current_cat.data(Qt.UserRole) if current_cat else "all"

            search_text = self._search_input.text().strip()

            sql = "SELECT * FROM vault_entries WHERE 1=1"
            params = []

            if cat_key == "favorite":
                sql += " AND is_favorite = 1"
            elif cat_key != "all":
                sql += " AND category = ?"
                params.append(cat_key)

            if search_text:
                sql += " AND (title LIKE ? OR username LIKE ? OR url LIKE ? OR notes LIKE ?)"
                like = f"%{search_text}%"
                params.extend([like, like, like, like])

            sql += " ORDER BY is_favorite DESC, updated_at DESC"

            rows = db.execute(sql, params).fetchall()
            entries = [dict(row) for row in rows]
        finally:
            db.close()

        # 更新列表
        self._entries_list.clear()
        for entry in entries:
            fav = "⭐ " if entry["is_favorite"] else ""
            cat_name = CATEGORIES.get(entry["category"], ("",))[0]
            display = f"{fav}{entry['title']}"
            if cat_name:
                display += f"  ({cat_name})"

            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, entry)

            # 副标题：用户名
            username = entry.get("username", "")
            if username:
                item.setToolTip(f"用户名: {username}")

            self._entries_list.addItem(item)

        self._status_label.setText(f"共 {len(entries)} 个条目")

    def _on_category_changed(self, current, previous):
        """分类切换"""
        self._refresh_entries()

    def _on_search(self, text):
        """搜索"""
        self._refresh_entries()

    def _on_add_entry(self):
        """添加条目"""
        if self._is_locked:
            return

        dialog = EntryEditDialog(
            master_password=self._master_password,
            salt=self._salt,
            parent=self,
        )
        if dialog.exec_() != QDialog.Accepted or not dialog.result_data:
            return

        db = self.get_db()
        try:
            data = dialog.result_data
            db.execute(
                """INSERT INTO vault_entries
                   (category, title, username, password_encrypted, url, notes, is_favorite)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (data["category"], data["title"], data["username"],
                 data["password_encrypted"], data["url"], data["notes"],
                 data["is_favorite"]),
            )
            db.commit()
        finally:
            db.close()

        self._refresh_entries()
        InfoBar.success("已添加", f"「{data['title']}」已保存", parent=self, duration=2000, position=InfoBarPosition.TOP)

    def _on_edit_entry_item(self, item):
        """双击编辑条目"""
        entry = item.data(Qt.UserRole)
        if not entry:
            return
        self._edit_entry(entry)

    def _edit_entry(self, entry):
        """编辑条目"""
        if self._is_locked:
            return

        dialog = EntryEditDialog(
            entry=entry,
            master_password=self._master_password,
            salt=self._salt,
            parent=self,
        )
        if dialog.exec_() != QDialog.Accepted or not dialog.result_data:
            return

        db = self.get_db()
        try:
            data = dialog.result_data
            db.execute(
                """UPDATE vault_entries
                   SET category=?, title=?, username=?, password_encrypted=?,
                       url=?, notes=?, is_favorite=?, updated_at=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (data["category"], data["title"], data["username"],
                 data["password_encrypted"], data["url"], data["notes"],
                 data["is_favorite"], entry["id"]),
            )
            db.commit()
        finally:
            db.close()

        self._refresh_entries()
        InfoBar.success("已更新", f"「{data['title']}」已更新", parent=self, duration=2000, position=InfoBarPosition.TOP)

    def _delete_entry(self, entry):
        """删除条目"""
        from qfluentwidgets import MessageBox

        msg = MessageBox("确认删除", f"确定要删除「{entry['title']}」吗？\n此操作不可恢复。", self)
        if not msg.exec():
            return

        db = self.get_db()
        try:
            db.execute("DELETE FROM vault_entries WHERE id = ?", (entry["id"],))
            db.commit()
        finally:
            db.close()

        self._refresh_entries()
        InfoBar.success("已删除", f"「{entry['title']}」已删除", parent=self, duration=2000, position=InfoBarPosition.TOP)

    def _toggle_favorite(self, entry):
        """切换收藏"""
        db = self.get_db()
        try:
            new_val = 0 if entry["is_favorite"] else 1
            db.execute(
                "UPDATE vault_entries SET is_favorite = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_val, entry["id"]),
            )
            db.commit()
        finally:
            db.close()

        self._refresh_entries()

    def _copy_field(self, entry, field):
        """复制字段到剪贴板（30秒后自动清除）"""
        if field == "username":
            text = entry.get("username", "")
        elif field == "password":
            encrypted = entry.get("password_encrypted", "")
            if not encrypted:
                return
            try:
                text = decrypt_password(encrypted, self._master_password, self._salt)
            except Exception:
                InfoBar.error("错误", "解密失败", parent=self, duration=2000)
                return
        elif field == "url":
            text = entry.get("url", "")
        else:
            return

        if not text:
            return

        clipboard = QApplication.clipboard()
        clipboard.setText(text)

        # 30秒后自动清除剪贴板
        if self._clipboard_timer:
            self._clipboard_timer.stop()
        self._clipboard_timer = QTimer()
        self._clipboard_timer.setSingleShot(True)
        self._clipboard_timer.timeout.connect(lambda: clipboard.clear())
        self._clipboard_timer.start(30000)

        field_names = {"username": "用户名", "password": "密码", "url": "网址"}
        InfoBar.success(
            "已复制",
            f"{field_names[field]}已复制到剪贴板（30秒后自动清除）",
            parent=self,
            duration=2500,
            position=InfoBarPosition.TOP,
        )

    def _on_entry_context_menu(self, pos):
        """右键菜单"""
        item = self._entries_list.itemAt(pos)
        if not item:
            return

        entry = item.data(Qt.UserRole)
        if not entry:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { font-size: 13px; padding: 4px; }
            QMenu::item { padding: 6px 24px; }
            QMenu::item:selected { background: #e8f0fe; }
        """)

        copy_user = menu.addAction("📋 复制用户名")
        copy_user.triggered.connect(lambda: self._copy_field(entry, "username"))

        copy_pwd = menu.addAction("📋 复制密码")
        copy_pwd.triggered.connect(lambda: self._copy_field(entry, "password"))

        copy_url = menu.addAction("📋 复制网址")
        copy_url.triggered.connect(lambda: self._copy_field(entry, "url"))

        menu.addSeparator()

        fav_text = "⭐ 取消收藏" if entry["is_favorite"] else "⭐ 添加收藏"
        toggle_fav = menu.addAction(fav_text)
        toggle_fav.triggered.connect(lambda: self._toggle_favorite(entry))

        menu.addSeparator()

        edit_action = menu.addAction("✏️ 编辑")
        edit_action.triggered.connect(lambda: self._edit_entry(entry))

        delete_action = menu.addAction("🗑️ 删除")
        delete_action.triggered.connect(lambda: self._delete_entry(entry))

        menu.exec_(self._entries_list.mapToGlobal(pos))

    def on_deactivate(self):
        """关闭时自动锁定"""
        super().on_deactivate()
        self._lock()