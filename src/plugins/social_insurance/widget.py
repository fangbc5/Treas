"""五险一金计算器 - 计算社保、公积金、个税及年终奖"""

import sys
import os

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLineEdit, QLabel, QComboBox, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QSizePolicy, QScrollArea, QWidget,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

_project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.core.plugin_base import PluginBase


# 七级累进税率表（综合所得）
TAX_BRACKETS = [
    (36000, 0.03, 0),
    (144000, 0.10, 2520),
    (300000, 0.20, 16920),
    (420000, 0.25, 31920),
    (660000, 0.30, 52920),
    (960000, 0.35, 85920),
    (float('inf'), 0.45, 181920),
]

# 统一的 QGroupBox 样式（和 currency_converter 一致）
GROUP_STYLE = """
    QGroupBox {
        font-size: 14px; font-weight: bold;
        border: 1px solid #ddd; border-radius: 8px;
        margin-top: 12px; padding-top: 16px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px; padding: 0 6px;
    }
"""

INPUT_STYLE = """
    padding: 8px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px;
"""


def calc_tax(taxable_income: float) -> float:
    """根据应纳税所得额计算个税（七级累进）"""
    if taxable_income <= 0:
        return 0.0
    for upper, rate, deduction in TAX_BRACKETS:
        if taxable_income <= upper:
            return taxable_income * rate - deduction
    return 0.0


class PluginWidget(PluginBase):
    """五险一金计算器"""

    plugin_id = "social_insurance"
    plugin_name = "五险一金计算器"
    plugin_version = "1.0.0"
    plugin_description = "计算五险一金明细、工资个税及年终奖单独计税"
    plugin_icon = "BOOK_SHELF"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # 标题
        title = QLabel("🧮 五险一金计算器")
        title.setFont(QFont("", 16, QFont.Bold))
        layout.addWidget(title)

        # 提示
        hint = QLabel("计算五险一金明细、工资个税及年终奖单独计税")
        hint.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(hint)

        # === 输入区 ===
        # 月薪
        row0 = QHBoxLayout()
        row0.addWidget(QLabel("月薪:"))
        self.salary_input = QLineEdit("10000")
        self.salary_input.setPlaceholderText("输入月薪")
        self.salary_input.setStyleSheet(
            "padding: 8px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px;"
        )
        row0.addWidget(self.salary_input)
        layout.addLayout(row0)

        # 年终奖
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("年终奖:"))
        self.bonus_input = QLineEdit("0")
        self.bonus_input.setPlaceholderText("输入年终奖")
        self.bonus_input.setStyleSheet(
            "padding: 8px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px;"
        )
        row1.addWidget(self.bonus_input)
        layout.addLayout(row1)

        # 公积金比例
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("公积金比例:"))
        self.fund_ratio = QComboBox()
        self.fund_ratio.addItems(
            ["5%", "6%", "7%", "8%", "9%", "10%", "11%", "12%"]
        )
        self.fund_ratio.setCurrentIndex(6)
        row2.addWidget(self.fund_ratio)
        layout.addLayout(row2)

        # 计算按钮
        calc_btn = QPushButton("开始计算")
        calc_btn.setStyleSheet("""
            QPushButton {
                background: #4a90d9; color: white; border: none;
                border-radius: 6px; font-size: 14px; padding: 8px 24px;
            }
            QPushButton:hover { background: #357abd; }
            QPushButton:pressed { background: #2a6aad; }
        """)
        calc_btn.clicked.connect(self._calculate)
        layout.addWidget(calc_btn)

        # === 五险一金明细 ===
        ins_group = QGroupBox("月度五险一金明细")
        ins_group.setStyleSheet(GROUP_STYLE)
        ins_layout = QVBoxLayout(ins_group)

        self.insurance_table = QTableWidget()
        self.insurance_table.setColumnCount(5)
        self.insurance_table.setHorizontalHeaderLabels(
            ["项目", "个人比例", "个人金额", "单位比例", "单位金额"]
        )
        self.insurance_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.insurance_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.insurance_table.verticalHeader().setVisible(False)
        self.insurance_table.setMaximumHeight(220)
        ins_layout.addWidget(self.insurance_table)

        layout.addWidget(ins_group)

        # === 个税计算 ===
        tax_group = QGroupBox("个税计算")
        tax_group.setStyleSheet(GROUP_STYLE)
        self.tax_layout = QVBoxLayout(tax_group)
        layout.addWidget(tax_group)

        # === 年度汇总 ===
        summary_group = QGroupBox("年度汇总")
        summary_group.setStyleSheet(GROUP_STYLE)
        self.summary_layout = QVBoxLayout(summary_group)
        layout.addWidget(summary_group)

        layout.addStretch()

        # 默认计算一次
        self._calculate()

    def _calculate(self):
        try:
            salary = int(self.salary_input.text() or "0")
        except ValueError:
            salary = 0
        try:
            bonus = int(self.bonus_input.text() or "0")
        except ValueError:
            bonus = 0
        fund_pct = int(self.fund_ratio.currentText().rstrip("%"))

        # 五险一金比例（个人 / 单位）
        items = [
            ("养老保险", 0.08, 0.16),
            ("医疗保险", 0.02, 0.08),
            ("失业保险", 0.005, 0.005),
            ("工伤保险", 0.0, 0.005),
            ("生育保险", 0.0, 0.008),
            ("住房公积金", fund_pct / 100.0, fund_pct / 100.0),
        ]

        personal_total = 0.0
        employer_total = 0.0
        rows = []

        for name, p_rate, e_rate in items:
            p_amount = round(salary * p_rate, 2)
            e_amount = round(salary * e_rate, 2)
            personal_total += p_amount
            employer_total += e_amount
            rows.append((
                name,
                f"{p_rate*100:.1f}%",
                f"{p_amount:.2f}",
                f"{e_rate*100:.1f}%",
                f"{e_amount:.2f}",
            ))

        rows.append(("合计", "-", f"{personal_total:.2f}", "-", f"{employer_total:.2f}"))

        # 更新表格
        self.insurance_table.setRowCount(len(rows))
        for r, row_data in enumerate(rows):
            for c, text in enumerate(row_data):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                if r == len(rows) - 1:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.insurance_table.setItem(r, c, item)

        # 月度工资个税
        monthly_taxable = salary - personal_total - 5000
        monthly_tax = calc_tax(monthly_taxable * 12) / 12
        monthly_after_tax = salary - personal_total - monthly_tax

        # 年终奖单独计税
        if bonus > 0:
            monthly_bonus = bonus / 12
            bonus_tax = 0.0
            for upper, rate, deduction in TAX_BRACKETS:
                if monthly_bonus <= upper:
                    bonus_tax = bonus * rate - deduction
                    break
        else:
            bonus_tax = 0.0
        bonus_after_tax = bonus - bonus_tax

        # 更新个税区域
        self._clear_layout(self.tax_layout)
        self.tax_layout.addWidget(self._make_kv(
            "月度应纳税所得额", f"{monthly_taxable:.2f} 元"
        ))
        self.tax_layout.addWidget(self._make_kv(
            "月度工资个税", f"{monthly_tax:.2f} 元"
        ))
        self.tax_layout.addWidget(self._make_kv(
            "月度税后工资", f"{monthly_after_tax:.2f} 元"
        ))
        self.tax_layout.addWidget(self._make_kv(
            "年终奖", f"{bonus:.2f} 元"
        ))
        self.tax_layout.addWidget(self._make_kv(
            "年终奖个税（单独计税）", f"{bonus_tax:.2f} 元"
        ))
        self.tax_layout.addWidget(self._make_kv(
            "年终奖税后金额", f"{bonus_after_tax:.2f} 元"
        ))

        # 年度汇总
        annual_gross = salary * 12 + bonus
        annual_personal = personal_total * 12
        annual_employer = employer_total * 12
        annual_tax = monthly_tax * 12 + bonus_tax
        annual_net = monthly_after_tax * 12 + bonus_after_tax

        self._clear_layout(self.summary_layout)
        summary_items = [
            ("年度税前总收入", f"{annual_gross:.2f} 元"),
            ("年度个人五险一金", f"{annual_personal:.2f} 元"),
            ("年度单位五险一金", f"{annual_employer:.2f} 元"),
            ("年度工资个税", f"{monthly_tax * 12:.2f} 元"),
            ("年终奖个税", f"{bonus_tax:.2f} 元"),
            ("年度总个税", f"{annual_tax:.2f} 元"),
            ("年度到手收入", f"{annual_net:.2f} 元"),
            ("单位年度总成本", f"{salary * 12 + annual_employer:.2f} 元"),
        ]
        for key, val in summary_items:
            self.summary_layout.addWidget(self._make_kv(key, val))

    def _make_kv(self, key: str, value: str) -> QLabel:
        """创建一行 key: value 文本"""
        label = QLabel(f"{key}：{value}")
        label.setStyleSheet("font-size: 13px; padding: 2px 0;")
        return label

    @staticmethod
    def _clear_layout(layout):
        """清除 layout 中的所有子项"""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()