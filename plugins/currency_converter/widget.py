"""汇率换算插件 - 常用货币汇率换算"""

import sys
import os

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLineEdit, QLabel, QComboBox,
    QGroupBox, QSizePolicy,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

_project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.core.plugin_base import PluginBase


# 内置汇率数据 (相对于 USD)
RATES_TO_USD = {
    "USD": 1.0, "CNY": 7.25, "EUR": 0.92, "GBP": 0.79,
    "JPY": 157.50, "KRW": 1370.0, "HKD": 7.82, "TWD": 32.50,
    "SGD": 1.35, "AUD": 1.53, "CAD": 1.37, "CHF": 0.89,
    "THB": 36.50, "MYR": 4.72, "INR": 83.50,
}

CURRENCY_NAMES = {
    "USD": "美元", "CNY": "人民币", "EUR": "欧元", "GBP": "英镑",
    "JPY": "日元", "KRW": "韩元", "HKD": "港币", "TWD": "新台币",
    "SGD": "新加坡元", "AUD": "澳元", "CAD": "加元", "CHF": "瑞士法郎",
    "THB": "泰铢", "MYR": "马来西亚元", "INR": "印度卢比",
}


class CurrencyConverterWidget(PluginBase):
    """汇率换算插件"""

    plugin_id = "currency_converter"
    plugin_name = "汇率换算"
    plugin_version = "1.0.0"
    plugin_description = "常用货币汇率换算工具，支持多种货币之间的转换"
    plugin_icon = "fa5s.exchange-alt"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # 标题
        title = QLabel("💱 汇率换算工具")
        title.setFont(QFont("", 16, QFont.Bold))
        layout.addWidget(title)

        # 提示
        hint = QLabel("汇率数据为参考值，实际交易请以银行汇率为准")
        hint.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(hint)

        # === 输入区 ===
        input_group = QGroupBox("货币换算")
        input_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px; font-weight: bold;
                border: 1px solid #ddd; border-radius: 8px;
                margin-top: 12px; padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px; padding: 0 6px;
            }
        """)
        input_layout = QGridLayout(input_group)

        # 源货币
        input_layout.addWidget(QLabel("金额:"), 0, 0)
        self.amount_input = QLineEdit("100")
        self.amount_input.setPlaceholderText("输入金额")
        self.amount_input.setStyleSheet(
            "padding: 8px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px;"
        )
        self.amount_input.textChanged.connect(self._convert)
        input_layout.addWidget(self.amount_input, 0, 1)

        self.from_combo = QComboBox()
        self._populate_combo(self.from_combo)
        self.from_combo.setCurrentText("CNY")
        self.from_combo.currentIndexChanged.connect(self._convert)
        input_layout.addWidget(self.from_combo, 0, 2)

        # 交换按钮
        swap_btn = QPushButton("⇄")
        swap_btn.setFixedSize(40, 40)
        swap_btn.setStyleSheet("""
            QPushButton {
                background: #4a90d9; color: white; border: none;
                border-radius: 20px; font-size: 18px;
            }
            QPushButton:hover { background: #357abd; }
        """)
        swap_btn.clicked.connect(self._swap)
        input_layout.addWidget(swap_btn, 1, 1, Qt.AlignCenter)

        # 目标货币
        input_layout.addWidget(QLabel("结果:"), 2, 0)
        self.result_label = QLabel("--")
        self.result_label.setFont(QFont("", 18, QFont.Bold))
        self.result_label.setStyleSheet("color: #34c759;")
        input_layout.addWidget(self.result_label, 2, 1)

        self.to_combo = QComboBox()
        self._populate_combo(self.to_combo)
        self.to_combo.setCurrentText("USD")
        self.to_combo.currentIndexChanged.connect(self._convert)
        input_layout.addWidget(self.to_combo, 2, 2)

        layout.addWidget(input_group)

        # === 汇率信息 ===
        self.rate_info = QLabel("")
        self.rate_info.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.rate_info)

        # === 常用汇率表 ===
        table_group = QGroupBox("常用汇率 (基于 1 CNY)")
        table_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px; font-weight: bold;
                border: 1px solid #ddd; border-radius: 8px;
                margin-top: 12px; padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px; padding: 0 6px;
            }
        """)
        table_layout = QGridLayout(table_group)

        currencies = ["USD", "EUR", "GBP", "JPY", "HKD", "KRW"]
        for i, code in enumerate(currencies):
            rate = RATES_TO_USD[code] / RATES_TO_USD["CNY"]
            lbl = QLabel(f"{CURRENCY_NAMES.get(code, code)} ({code})")
            val = QLabel(f"{rate:.4f}")
            val.setStyleSheet("font-weight: bold;")
            row = i // 2
            col = (i % 2) * 2
            table_layout.addWidget(lbl, row, col)
            table_layout.addWidget(val, row, col + 1)

        layout.addWidget(table_group)
        layout.addStretch()

        # 初始计算
        self._convert()

    def _populate_combo(self, combo: QComboBox):
        for code in RATES_TO_USD:
            name = CURRENCY_NAMES.get(code, code)
            combo.addItem(f"{code} - {name}", code)

    def _convert(self):
        try:
            amount = float(self.amount_input.text())
        except ValueError:
            self.result_label.setText("--")
            self.rate_info.setText("")
            return

        from_code = self.from_combo.currentData()
        to_code = self.to_combo.currentData()

        if not from_code or not to_code:
            return

        # 转换: 先转 USD，再转目标
        usd_amount = amount / RATES_TO_USD[from_code]
        result = usd_amount * RATES_TO_USD[to_code]

        self.result_label.setText(f"{result:,.2f}")

        rate = RATES_TO_USD[to_code] / RATES_TO_USD[from_code]
        from_name = CURRENCY_NAMES.get(from_code, from_code)
        to_name = CURRENCY_NAMES.get(to_code, to_code)
        self.rate_info.setText(
            f"1 {from_name} = {rate:.4f} {to_name}"
        )

    def _swap(self):
        from_idx = self.from_combo.currentIndex()
        to_idx = self.to_combo.currentIndex()
        self.from_combo.setCurrentIndex(to_idx)
        self.to_combo.setCurrentIndex(from_idx)