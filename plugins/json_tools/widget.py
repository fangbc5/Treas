"""JSON 格式化与对比工具"""

import sys
import os
import json
import difflib
import re
import html as html_mod

_project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QApplication, QWidget,
    QFileDialog, QSplitter, QTabWidget, QTextEdit,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import (
    QTextCharFormat, QColor, QFont, QSyntaxHighlighter,
    QTextDocument,
)

from qfluentwidgets import (
    PushButton, PrimaryPushButton, CaptionLabel, TitleLabel,
    InfoBar, InfoBarPosition, TextEdit as FluentTextEdit,
)

from src.core.plugin_base import PluginBase


# ── JSON 语法高亮 ──────────────────────────────────────────────

class JsonHighlighter(QSyntaxHighlighter):
    """JSON 语法高亮器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules = []
        # 键名（字符串后跟冒号）
        fmt_key = QTextCharFormat()
        fmt_key.setForeground(QColor("#9cdcfe"))
        self._rules.append((r'"[^"\\]*(?:\\.[^"\\]*)*"\s*:', fmt_key))
        # 字符串值
        fmt_str = QTextCharFormat()
        fmt_str.setForeground(QColor("#ce9178"))
        self._rules.append((r'"[^"\\]*(?:\\.[^"\\]*)*"', fmt_str))
        # 数字
        fmt_num = QTextCharFormat()
        fmt_num.setForeground(QColor("#b5cea8"))
        self._rules.append((r'\b-?\d+\.?\d*(?:[eE][+-]?\d+)?\b', fmt_num))
        # 布尔 / null
        fmt_kw = QTextCharFormat()
        fmt_kw.setForeground(QColor("#569cd6"))
        self._rules.append((r'\b(true|false|null)\b', fmt_kw))

    def highlightBlock(self, text):
        for pattern, fmt in self._rules:
            for m in re.finditer(pattern, text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)


# ── Diff 结果展示 ──────────────────────────────────────────────

class DiffView(QTextEdit):
    """Diff 结果展示（只读，带行号着色）"""

    COLORS = {
        "+": QColor("#1e4d2b"),   # 新增 - 深绿背景
        "-": QColor("#5c1a1a"),   # 删除 - 深红背景
        "?": QColor("#6b4c00"),   # 行内差异标记
        "@": QColor("#1a3a5c"),   # 位置信息
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Menlo", 12))
        self.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; border: none;")

    def show_diff(self, text1: str, text2: str):
        """显示两个文本的差异"""
        lines1 = text1.splitlines(keepends=True)
        lines2 = text2.splitlines(keepends=True)
        diff = difflib.unified_diff(lines1, lines2, lineterm="", fromfile="左侧", tofile="右侧")
        diff_lines = list(diff)

        if not diff_lines:
            self.setHtml(
                '<p style="color: #4ec9b0; font-size: 16px; text-align: center;">✅ 两段文本完全一致</p>'
            )
            return

        html_parts = []
        for line in diff_lines:
            escaped = html_mod.escape(line)
            prefix = line[0] if line else " "
            bg = self.COLORS.get(prefix)
            if bg:
                html_parts.append(
                    f'<div style="background-color: {bg.name()}; '
                    f'white-space: pre; font-family: Menlo, monospace;">{escaped}</div>'
                )
            else:
                html_parts.append(
                    f'<div style="white-space: pre; font-family: Menlo, monospace;">{escaped}</div>'
                )
        self.setHtml("".join(html_parts))


# ── 主 Widget ──────────────────────────────────────────────────

class JsonToolsWidget(PluginBase):
    """JSON 格式化与对比工具"""

    plugin_id = "json_tools"
    plugin_name = "JSON 格式化与对比"
    plugin_version = "1.0.0"
    plugin_description = "JSON 格式化/压缩/校验 + 文本对比 + 文件内容对比工具"
    plugin_icon = "CODE"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        layout.addWidget(TitleLabel("🔧 JSON 格式化与对比"))

        # 标签页
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._init_format_tab()
        self._init_diff_tab()
        self._init_file_diff_tab()
        layout.addWidget(self._tabs)

    # ── Tab 1: JSON 格式化 ──

    def _init_format_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setSpacing(8)

        # 按钮
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        format_btn = PrimaryPushButton("✨ 格式化")
        format_btn.clicked.connect(self._format_json)
        btn_row.addWidget(format_btn)
        minify_btn = PushButton("📦 压缩")
        minify_btn.clicked.connect(self._minify_json)
        btn_row.addWidget(minify_btn)
        sort_btn = PushButton("🔤 键排序")
        sort_btn.clicked.connect(self._sort_json)
        btn_row.addWidget(sort_btn)
        copy_btn = PushButton("📋 复制结果")
        copy_btn.clicked.connect(self._copy_formatted)
        btn_row.addWidget(copy_btn)
        clear_btn = PushButton("🗑️ 清除")
        clear_btn.clicked.connect(lambda: (self._json_input.clear(), self._json_output.clear()))
        btn_row.addWidget(clear_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        # 分栏：输入 / 输出
        splitter = QSplitter(Qt.Horizontal)
        self._json_input = QTextEdit()
        self._json_input.setPlaceholderText("在此粘贴 JSON...")
        self._json_input.setFont(QFont("Menlo", 12))
        self._json_input.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        self._json_input_hl = JsonHighlighter(self._json_input.document())
        splitter.addWidget(self._json_input)

        self._json_output = QTextEdit()
        self._json_output.setReadOnly(True)
        self._json_output.setFont(QFont("Menlo", 12))
        self._json_output.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        self._json_output_hl = JsonHighlighter(self._json_output.document())
        splitter.addWidget(self._json_output)
        splitter.setSizes([500, 500])
        lay.addWidget(splitter, 1)

        self._tabs.addTab(tab, "📝 JSON 格式化")

    def _format_json(self):
        text = self._json_input.toPlainText().strip()
        if not text:
            return
        try:
            obj = json.loads(text)
            formatted = json.dumps(obj, indent=4, ensure_ascii=False)
            self._json_output.setPlainText(formatted)
        except json.JSONDecodeError as e:
            self._json_output.setPlainText(f"❌ JSON 语法错误:\n{e}")
            self._json_output.setStyleSheet("background-color: #1e1e1e; color: #f44747;")

    def _minify_json(self):
        text = self._json_input.toPlainText().strip()
        if not text:
            return
        try:
            obj = json.loads(text)
            minified = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
            self._json_output.setPlainText(minified)
        except json.JSONDecodeError as e:
            self._json_output.setPlainText(f"❌ JSON 语法错误:\n{e}")

    def _sort_json(self):
        text = self._json_input.toPlainText().strip()
        if not text:
            return
        try:
            obj = json.loads(text)
            sorted_json = json.dumps(self._sort_keys(obj), indent=4, ensure_ascii=False, sort_keys=False)
            self._json_output.setPlainText(sorted_json)
        except json.JSONDecodeError as e:
            self._json_output.setPlainText(f"❌ JSON 语法错误:\n{e}")

    def _sort_keys(self, obj):
        if isinstance(obj, dict):
            return {k: self._sort_keys(v) for k, v in sorted(obj.items())}
        if isinstance(obj, list):
            return [self._sort_keys(i) for i in obj]
        return obj

    def _copy_formatted(self):
        text = self._json_output.toPlainText()
        if text and not text.startswith("❌"):
            QApplication.clipboard().setText(text)
            InfoBar.success("已复制", "格式化结果已复制到剪贴板",
                            parent=self, duration=1500, position=InfoBarPosition.TOP)

    # ── Tab 2: 文本对比 ──

    def _init_diff_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setSpacing(8)

        # 按钮
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        diff_btn = PrimaryPushButton("🔍 对比")
        diff_btn.clicked.connect(self._do_text_diff)
        btn_row.addWidget(diff_btn)
        swap_btn = PushButton("🔄 交换")
        swap_btn.clicked.connect(self._swap_diff)
        btn_row.addWidget(swap_btn)
        clear_btn = PushButton("🗑️ 清除")
        clear_btn.clicked.connect(lambda: (self._diff_left.clear(), self._diff_right.clear(), self._diff_view.clear()))
        btn_row.addWidget(clear_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        # 分栏：左右输入
        input_splitter = QSplitter(Qt.Horizontal)
        self._diff_left = QTextEdit()
        self._diff_left.setPlaceholderText("左侧文本 / JSON...")
        self._diff_left.setFont(QFont("Menlo", 12))
        self._diff_left.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        self._diff_left_hl = JsonHighlighter(self._diff_left.document())
        input_splitter.addWidget(self._diff_left)

        self._diff_right = QTextEdit()
        self._diff_right.setPlaceholderText("右侧文本 / JSON...")
        self._diff_right.setFont(QFont("Menlo", 12))
        self._diff_right.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        self._diff_right_hl = JsonHighlighter(self._diff_right.document())
        input_splitter.addWidget(self._diff_right)
        input_splitter.setSizes([500, 500])
        lay.addWidget(input_splitter, 2)

        # Diff 结果
        self._diff_view = DiffView()
        self._diff_view.setMaximumHeight(250)
        lay.addWidget(self._diff_view, 1)

        self._tabs.addTab(tab, "🔍 文本对比")

    def _do_text_diff(self):
        left = self._diff_left.toPlainText()
        right = self._diff_right.toPlainText()
        if not left and not right:
            return
        self._diff_view.show_diff(left, right)

    def _swap_diff(self):
        left = self._diff_left.toPlainText()
        right = self._diff_right.toPlainText()
        self._diff_left.setPlainText(right)
        self._diff_right.setPlainText(left)

    # ── Tab 3: 文件对比 ──

    def _init_file_diff_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setSpacing(8)

        # 文件选择
        file_row = QHBoxLayout()
        file_row.setSpacing(8)
        self._file1_label = CaptionLabel("文件 1：未选择")
        file_row.addWidget(self._file1_label, 1)
        f1_btn = PushButton("📂 选择文件 1")
        f1_btn.clicked.connect(lambda: self._pick_file(1))
        file_row.addWidget(f1_btn)
        file_row.addSpacing(16)
        self._file2_label = CaptionLabel("文件 2：未选择")
        file_row.addWidget(self._file2_label, 1)
        f2_btn = PushButton("📂 选择文件 2")
        f2_btn.clicked.connect(lambda: self._pick_file(2))
        file_row.addWidget(f2_btn)
        lay.addLayout(file_row)

        # 对比按钮
        btn_row = QHBoxLayout()
        diff_btn = PrimaryPushButton("🔍 对比文件")
        diff_btn.clicked.connect(self._do_file_diff)
        btn_row.addWidget(diff_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        # Diff 结果
        self._file_diff_view = DiffView()
        lay.addWidget(self._file_diff_view, 1)

        self._tabs.addTab(tab, "📄 文件对比")

    def _pick_file(self, which):
        path, _ = QFileDialog.getOpenFileName(self, f"选择文件 {which}", "", "所有文件 (*);;JSON (*.json);;文本 (*.txt)")
        if path:
            label = self._file1_label if which == 1 else self._file2_label
            label.setText(f"文件 {which}：{os.path.basename(path)}")
            label.setToolTip(path)
            if which == 1:
                self._file1_path = path
            else:
                self._file2_path = path

    def _do_file_diff(self):
        path1 = getattr(self, "_file1_path", None)
        path2 = getattr(self, "_file2_path", None)
        if not path1 or not path2:
            InfoBar.warning("请选择文件", "请先选择两个文件进行对比",
                            parent=self, duration=2000, position=InfoBarPosition.TOP)
            return
        try:
            with open(path1, "r", encoding="utf-8") as f:
                text1 = f.read()
            with open(path2, "r", encoding="utf-8") as f:
                text2 = f.read()
            self._file_diff_view.show_diff(text1, text2)
        except Exception as e:
            self._file_diff_view.setPlainText(f"❌ 读取文件失败:\n{e}")