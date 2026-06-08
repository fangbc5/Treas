"""简易记账本插件 - 轻量级收支记录"""

import sys
import os
import sqlite3
from datetime import datetime

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLineEdit, QLabel, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QDateEdit, QMessageBox, QAbstractItemView,
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont, QColor

_project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.core.plugin_base import PluginBase

# 记账类型
EXPENSE_CATEGORIES = ["餐饮", "交通", "购物", "住房", "娱乐", "医疗", "教育", "其他支出"]
INCOME_CATEGORIES = ["工资", "投资", "兼职", "红包", "其他收入"]

# 颜色
COLOR_INCOME = "#34c759"
COLOR_EXPENSE = "#ff3b30"


class SimpleLedgerWidget(PluginBase):
    """简易记账本插件"""

    plugin_id = "simple_ledger"
    plugin_name = "简易记账本"
    plugin_version = "1.0.0"
    plugin_description = "轻量级收支记录工具，支持添加、查看和统计日常收支"
    plugin_icon = "fa5s.book"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_db()
        self._init_ui()
        self._refresh_data()

    def _init_db(self):
        """初始化插件本地数据库"""
        data_dir = os.path.join(_project_root, "data")
        os.makedirs(data_dir, exist_ok=True)
        self.db_path = os.path.join(data_dir, "ledger.db")

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                note TEXT DEFAULT '',
                record_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        # 标题
        title = QLabel("📒 简易记账本")
        title.setFont(QFont("", 16, QFont.Bold))
        layout.addWidget(title)

        # === 统计摘要 ===
        summary_layout = QHBoxLayout()

        self.income_label = QLabel("收入: ¥0.00")
        self.income_label.setFont(QFont("", 13, QFont.Bold))
        self.income_label.setStyleSheet(f"color: {COLOR_INCOME};")
        summary_layout.addWidget(self.income_label)

        self.expense_label = QLabel("支出: ¥0.00")
        self.expense_label.setFont(QFont("", 13, QFont.Bold))
        self.expense_label.setStyleSheet(f"color: {COLOR_EXPENSE};")
        summary_layout.addWidget(self.expense_label)

        self.balance_label = QLabel("结余: ¥0.00")
        self.balance_label.setFont(QFont("", 13, QFont.Bold))
        self.balance_label.setStyleSheet("color: #4a90d9;")
        summary_layout.addWidget(self.balance_label)

        summary_layout.addStretch()
        layout.addLayout(summary_layout)

        # === 添加记录 ===
        add_group = QGroupBox("添加记录")
        add_layout = QGridLayout(add_group)

        # 类型
        add_layout.addWidget(QLabel("类型:"), 0, 0)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["支出", "收入"])
        self.type_combo.currentTextChanged.connect(self._update_categories)
        add_layout.addWidget(self.type_combo, 0, 1)

        # 分类
        add_layout.addWidget(QLabel("分类:"), 0, 2)
        self.category_combo = QComboBox()
        self._update_categories("支出")
        add_layout.addWidget(self.category_combo, 0, 3)

        # 金额
        add_layout.addWidget(QLabel("金额:"), 1, 0)
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("输入金额")
        add_layout.addWidget(self.amount_input, 1, 1)

        # 日期
        add_layout.addWidget(QLabel("日期:"), 1, 2)
        self.date_input = QDateEdit()
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("yyyy-MM-dd")
        add_layout.addWidget(self.date_input, 1, 3)

        # 备注
        add_layout.addWidget(QLabel("备注:"), 2, 0)
        self.note_input = QLineEdit()
        self.note_input.setPlaceholderText("可选备注")
        add_layout.addWidget(self.note_input, 2, 1, 1, 2)

        # 添加按钮
        add_btn = QPushButton("✚ 添加")
        add_btn.clicked.connect(self._add_record)
        add_layout.addWidget(add_btn, 2, 3)

        layout.addWidget(add_group)

        # === 记录列表 ===
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["日期", "类型", "分类", "金额", "备注", "操作"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

    def _update_categories(self, type_text: str):
        """更新分类下拉"""
        self.category_combo.clear()
        cats = EXPENSE_CATEGORIES if type_text == "支出" else INCOME_CATEGORIES
        self.category_combo.addItems(cats)

    def _add_record(self):
        """添加记录"""
        try:
            amount = float(self.amount_input.text())
        except ValueError:
            QMessageBox.warning(self, "提示", "请输入有效金额")
            return

        if amount <= 0:
            QMessageBox.warning(self, "提示", "金额必须大于0")
            return

        record_type = self.type_combo.currentText()
        category = self.category_combo.currentText()
        note = self.note_input.text().strip()
        date = self.date_input.date().toString("yyyy-MM-dd")

        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO records (type, category, amount, note, record_date) "
            "VALUES (?, ?, ?, ?, ?)",
            (record_type, category, amount, note, date),
        )
        conn.commit()
        conn.close()

        # 清空输入
        self.amount_input.clear()
        self.note_input.clear()

        self._refresh_data()

    def _delete_record(self, record_id: int):
        """删除记录"""
        reply = QMessageBox.question(
            self, "确认删除", "确定要删除这条记录吗？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            conn = sqlite3.connect(self.db_path)
            conn.execute("DELETE FROM records WHERE id = ?", (record_id,))
            conn.commit()
            conn.close()
            self._refresh_data()

    def _refresh_data(self):
        """刷新数据"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 统计
        income_result = cursor.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM records WHERE type = '收入'"
        ).fetchone()[0]
        expense_result = cursor.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM records WHERE type = '支出'"
        ).fetchone()[0]

        balance = income_result - expense_result

        self.income_label.setText(f"收入: ¥{income_result:,.2f}")
        self.expense_label.setText(f"支出: ¥{expense_result:,.2f}")
        self.balance_label.setText(f"结余: ¥{balance:,.2f}")

        # 记录列表
        rows = cursor.execute(
            "SELECT * FROM records ORDER BY record_date DESC, id DESC"
        ).fetchall()

        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(row["record_date"]))

            type_item = QTableWidgetItem(row["type"])
            if row["type"] == "收入":
                type_item.setForeground(QColor(COLOR_INCOME))
            else:
                type_item.setForeground(QColor(COLOR_EXPENSE))
            self.table.setItem(i, 1, type_item)

            self.table.setItem(i, 2, QTableWidgetItem(row["category"]))

            amount_item = QTableWidgetItem(f"¥{row['amount']:,.2f}")
            if row["type"] == "收入":
                amount_item.setForeground(QColor(COLOR_INCOME))
            else:
                amount_item.setForeground(QColor(COLOR_EXPENSE))
            self.table.setItem(i, 3, amount_item)

            self.table.setItem(i, 4, QTableWidgetItem(row["note"]))

            # 删除按钮
            del_btn = QPushButton("删除")
            del_btn.clicked.connect(
                lambda checked, rid=row["id"]: self._delete_record(rid)
            )
            self.table.setCellWidget(i, 5, del_btn)

        conn.close()