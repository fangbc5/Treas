"""五险一金计算器 - 累计预扣法个税计算、12个月明细及年终奖单独计税"""

import sys
import os

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QComboBox, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QSizePolicy, QWidget,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

_project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.core.plugin_base import PluginBase


# 七级累进税率表 - 综合所得（按年应纳税所得额）
# 来源：《中华人民共和国个人所得税法》第三条，2019年1月1日起施行
TAX_BRACKETS_ANNUAL = [
    (36000, 0.03, 0),        # 第1级：不超过36000元
    (144000, 0.10, 2520),     # 第2级：36000-144000元
    (300000, 0.20, 16920),    # 第3级：144000-300000元
    (420000, 0.25, 31920),    # 第4级：300000-420000元
    (660000, 0.30, 52920),    # 第5级：420000-660000元
    (960000, 0.35, 85920),    # 第6级：660000-960000元
    (float('inf'), 0.45, 181920),  # 第7级：超过960000元
]

# 月度税率表 - 用于年终奖单独计税（年终奖/12 找税率）
# 来源：国家税务总局公告2019年第11号
TAX_BRACKETS_MONTHLY = [
    (3000, 0.03, 0),
    (12000, 0.10, 210),
    (25000, 0.20, 1410),
    (35000, 0.25, 2660),
    (55000, 0.30, 4410),
    (80000, 0.35, 7160),
    (float('inf'), 0.45, 15160),
]

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


def calc_annual_tax(annual_taxable: float) -> float:
    """根据年应纳税所得额计算年度个税（七级累进，年度表）"""
    if annual_taxable <= 0:
        return 0.0
    for upper, rate, deduction in TAX_BRACKETS_ANNUAL:
        if annual_taxable <= upper:
            return annual_taxable * rate - deduction
    return 0.0


def calc_bonus_tax(bonus: float) -> float:
    """年终奖单独计税：奖金/12 → 月度税率表找税率，再乘以奖金"""
    if bonus <= 0:
        return 0.0
    monthly_bonus = bonus / 12
    for upper, rate, deduction in TAX_BRACKETS_MONTHLY:
        if monthly_bonus <= upper:
            return bonus * rate - deduction
    return 0.0


def _fit_table_height(table: QTableWidget):
    """让表格高度刚好容纳所有行（不出现滚动条）"""
    table.resizeRowsToContents()
    h = table.horizontalHeader().height()
    for r in range(table.rowCount()):
        h += table.rowHeight(r)
    table.setFixedHeight(h + 4)


def _set_table_item(table: QTableWidget, row: int, col: int, text: str,
                    bold: bool = False, bg_color: str = None):
    """设置表格单元格"""
    item = QTableWidgetItem(text)
    item.setTextAlignment(Qt.AlignCenter)
    if bold:
        f = item.font()
        f.setBold(True)
        item.setFont(f)
    if bg_color:
        item.setBackground(QColor(bg_color))
    table.setItem(row, col, item)


class PluginWidget(PluginBase):
    """五险一金计算器（累计预扣法）"""

    plugin_id = "social_insurance"
    plugin_name = "五险一金计算器"
    plugin_version = "2.0.0"
    plugin_description = "累计预扣法个税计算、12个月工资明细及年终奖单独计税"
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

        hint = QLabel("按累计预扣法逐月计算个税，真实反映每月工资差异\n（五险一金比例为参考值，各地政策不同）")
        hint.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(hint)

        # === 输入区 ===
        input_group = QGroupBox("基本参数")
        input_group.setStyleSheet(GROUP_STYLE)
        input_layout = QVBoxLayout(input_group)

        # 月薪
        row0 = QHBoxLayout()
        row0.addWidget(QLabel("月薪:"))
        self.salary_input = QLineEdit("10000")
        self.salary_input.setPlaceholderText("输入月薪（用于个税计算）")
        self.salary_input.setStyleSheet(INPUT_STYLE)
        row0.addWidget(self.salary_input)
        input_layout.addLayout(row0)

        # 社保基数
        row_base = QHBoxLayout()
        row_base.addWidget(QLabel("社保基数:"))
        self.base_input = QLineEdit("")
        self.base_input.setPlaceholderText("留空则与月薪相同")
        self.base_input.setStyleSheet(INPUT_STYLE)
        row_base.addWidget(self.base_input)
        input_layout.addLayout(row_base)

        # 年终奖（月薪倍数）
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("年终奖:"))
        self.bonus_input = QLineEdit("0")
        self.bonus_input.setPlaceholderText("月薪倍数（如1.5表示1.5倍月薪）")
        self.bonus_input.setStyleSheet(INPUT_STYLE)
        row1.addWidget(self.bonus_input)
        input_layout.addLayout(row1)

        # 年终奖发放月份
        row_bonus_month = QHBoxLayout()
        row_bonus_month.addWidget(QLabel("年终奖月份:"))
        self.bonus_month_combo = QComboBox()
        self.bonus_month_combo.addItems(
            [f"{i}月" for i in range(1, 13)]
        )
        self.bonus_month_combo.setCurrentIndex(11)  # 默认12月
        row_bonus_month.addWidget(self.bonus_month_combo)
        row_bonus_month.addStretch()
        input_layout.addLayout(row_bonus_month)

        # 公积金比例
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("公积金比例:"))
        self.fund_ratio = QComboBox()
        self.fund_ratio.addItems(
            ["5%", "6%", "7%", "8%", "9%", "10%", "11%", "12%"]
        )
        self.fund_ratio.setCurrentIndex(7)  # 默认 12%
        row2.addWidget(self.fund_ratio)
        row2.addStretch()
        input_layout.addLayout(row2)

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
        input_layout.addWidget(calc_btn)

        layout.addWidget(input_group)

        # === 五险一金明细 ===
        ins_group = QGroupBox("月度五险一金明细")
        ins_group.setStyleSheet(GROUP_STYLE)
        ins_layout = QVBoxLayout(ins_group)

        self.insurance_table = QTableWidget()
        self.insurance_table.setColumnCount(6)
        self.insurance_table.setHorizontalHeaderLabels(
            ["项目", "个人比例", "个人金额", "单位比例", "单位金额", "合计"]
        )
        self.insurance_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.insurance_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.insurance_table.verticalHeader().setVisible(False)
        self.insurance_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.insurance_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        ins_layout.addWidget(self.insurance_table)

        layout.addWidget(ins_group)

        # === 12个月工资明细 ===
        monthly_group = QGroupBox("12个月工资个税明细（累计预扣法）")
        monthly_group.setStyleSheet(GROUP_STYLE)
        monthly_layout = QVBoxLayout(monthly_group)

        self.monthly_table = QTableWidget()
        self.monthly_table.setColumnCount(8)
        self.monthly_table.setHorizontalHeaderLabels(
            ["月份", "月薪", "五险一金", "累计应纳税所得额",
             "适用税率", "当月个税", "当月到手", "备注"]
        )
        self.monthly_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.monthly_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.monthly_table.verticalHeader().setVisible(False)
        self.monthly_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.monthly_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        monthly_layout.addWidget(self.monthly_table)

        layout.addWidget(monthly_group)

        # === 年度汇总 ===
        summary_group = QGroupBox("年度汇总")
        summary_group.setStyleSheet(GROUP_STYLE)
        self.summary_layout = QVBoxLayout(summary_group)
        layout.addWidget(summary_group)

        layout.addStretch()

        # 默认计算一次
        self._calculate()

    def _calculate(self):
        # 解析输入
        try:
            salary = float(self.salary_input.text() or "0")
        except ValueError:
            salary = 0.0
        try:
            bonus_months = float(self.bonus_input.text() or "0")
        except ValueError:
            bonus_months = 0.0
        bonus = round(salary * bonus_months, 2)
        bonus_month = self.bonus_month_combo.currentIndex() + 1  # 1-12
        fund_pct = int(self.fund_ratio.currentText().rstrip("%"))

        # 社保基数（留空则与月薪相同）
        try:
            base = float(self.base_input.text() or "0")
            if base <= 0:
                base = salary
        except ValueError:
            base = salary

        # ============ 五险一金明细表 ============
        # 按社保基数计算，个人比例 / 单位比例
        items = [
            ("养老保险", 0.08, 0.16),          # 个人8%，单位16%
            ("医疗保险", 0.02, 0.098),          # 个人2%，单位9.8%
            ("大额医疗互助", None, None),        # 个人3元/月，单位固定
            ("失业保险", 0.005, 0.005),         # 个人0.5%，单位0.5%
            ("工伤保险", 0.0, 0.004),           # 个人0%，单位0.4%
            ("生育保险", 0.0, 0.008),           # 个人0%，单位0.8%
            ("住房公积金", fund_pct / 100.0, fund_pct / 100.0),
        ]

        personal_total = 0.0
        employer_total = 0.0
        ins_rows = []

        for name, p_rate, e_rate in items:
            # 大额医疗互助是固定金额
            if name == "大额医疗互助":
                p_amount = 3.0
                e_amount = round(base * 0.002, 2)
            else:
                p_amount = round(base * p_rate, 2)
                e_amount = round(base * e_rate, 2)

            total_amount = p_amount + e_amount
            personal_total += p_amount
            employer_total += e_amount

            if name == "大额医疗互助":
                ins_rows.append((
                    name,
                    "3元/月",
                    f"{p_amount:.2f}",
                    "0.2%",
                    f"{e_amount:.2f}",
                    f"{total_amount:.2f}",
                ))
            else:
                ins_rows.append((
                    name,
                    f"{p_rate * 100:.1f}%",
                    f"{p_amount:.2f}",
                    f"{e_rate * 100:.1f}%",
                    f"{e_amount:.2f}",
                    f"{total_amount:.2f}",
                ))

        ins_rows.append((
            "合计", "-", f"{personal_total:.2f}", "-",
            f"{employer_total:.2f}", f"{personal_total + employer_total:.2f}"
        ))

        self.insurance_table.setRowCount(len(ins_rows))
        for r, row_data in enumerate(ins_rows):
            for c, text in enumerate(row_data):
                _set_table_item(
                    self.insurance_table, r, c, text,
                    bold=(r == len(ins_rows) - 1),
                )
        _fit_table_height(self.insurance_table)

        # ============ 累计预扣法：逐月计算个税 ============
        monthly_data = []  # 每月数据: (month, salary, insurance, cum_taxable, rate, month_tax, month_net, note)
        cum_tax = 0.0  # 累计已缴个税
        annual_salary_tax = 0.0
        annual_net = 0.0
        annual_insurance = 0.0
        prev_bracket_idx = -1  # 上个月的税率档位，用于标注跳档

        for m in range(1, 13):
            # 累计应纳税所得额
            cum_income = salary * m
            cum_deduction = 5000 * m
            cum_insurance = personal_total * m
            cum_taxable = cum_income - cum_deduction - cum_insurance

            # 找税率档位
            bracket_idx = 0
            rate = 0.03
            deduction = 0
            for idx, (upper, r, d) in enumerate(TAX_BRACKETS_ANNUAL):
                if cum_taxable <= upper:
                    bracket_idx = idx
                    rate = r
                    deduction = d
                    break

            # 累计应纳税额
            cum_tax_amount = calc_annual_tax(cum_taxable)

            # 当月个税 = 累计应纳 - 累计已缴
            month_tax = max(0.0, cum_tax_amount - cum_tax)
            cum_tax = cum_tax_amount

            # 当月到手 = 月薪 - 五险一金 - 当月个税
            month_net = salary - personal_total - month_tax

            # 备注信息
            note = ""
            if m == bonus_month and bonus > 0:
                note = f"年终奖 {bonus:.2f}元（单独计税）"
            if bracket_idx > prev_bracket_idx and prev_bracket_idx >= 0:
                note = ("税率跳档↑ " + note).strip()

            monthly_data.append((
                m, salary, personal_total, cum_taxable, rate, month_tax, month_net, note
            ))
            annual_salary_tax += month_tax
            annual_net += month_net
            annual_insurance += personal_total
            prev_bracket_idx = bracket_idx

        # 年终奖单独计税
        bonus_tax = calc_bonus_tax(bonus)
        bonus_after_tax = bonus - bonus_tax

        # 填充12个月表格
        total_rows = len(monthly_data) + 1  # +1 合计行
        self.monthly_table.setRowCount(total_rows)
        for r, data in enumerate(monthly_data):
            m, sal, ins, cum_taxable, rate, m_tax, m_net, note = data
            _set_table_item(self.monthly_table, r, 0, f"{m}月")
            _set_table_item(self.monthly_table, r, 1, f"{sal:.2f}")
            _set_table_item(self.monthly_table, r, 2, f"{ins:.2f}")
            _set_table_item(self.monthly_table, r, 3, f"{cum_taxable:.2f}")
            _set_table_item(self.monthly_table, r, 4, f"{rate * 100:.0f}%")
            _set_table_item(self.monthly_table, r, 5, f"{m_tax:.2f}")
            _set_table_item(self.monthly_table, r, 6, f"{m_net:.2f}")
            _set_table_item(self.monthly_table, r, 7, note)

            # 跳档月份高亮背景
            if "跳档" in note:
                for c in range(8):
                    item = self.monthly_table.item(r, c)
                    if item:
                        item.setBackground(QColor("#FFF3E0"))

            # 年终奖月份高亮
            if m == bonus_month and bonus > 0:
                for c in range(8):
                    item = self.monthly_table.item(r, c)
                    if item:
                        item.setBackground(QColor("#E8F5E9"))

        # 合计行
        total_row = len(monthly_data)
        _set_table_item(self.monthly_table, total_row, 0, "合计", bold=True)
        _set_table_item(self.monthly_table, total_row, 1, f"{salary * 12:.2f}", bold=True)
        _set_table_item(self.monthly_table, total_row, 2, f"{annual_insurance:.2f}", bold=True)
        _set_table_item(self.monthly_table, total_row, 3, "-", bold=True)
        _set_table_item(self.monthly_table, total_row, 4, "-", bold=True)
        _set_table_item(self.monthly_table, total_row, 5, f"{annual_salary_tax:.2f}", bold=True)
        _set_table_item(self.monthly_table, total_row, 6, f"{annual_net:.2f}", bold=True)
        bonus_note = f"含年终奖税后 {bonus_after_tax:.2f}" if bonus > 0 else ""
        _set_table_item(self.monthly_table, total_row, 7, bonus_note, bold=True)

        _fit_table_height(self.monthly_table)

        # ============ 年度汇总 ============
        annual_gross = salary * 12 + bonus
        annual_employer = employer_total * 12
        total_tax = annual_salary_tax + bonus_tax
        total_net = annual_net + bonus_after_tax

        self._clear_layout(self.summary_layout)
        summary_items = [
            ("年度税前总收入", f"{annual_gross:.2f} 元"),
            ("年度个人五险一金", f"{annual_insurance:.2f} 元"),
            ("年度单位五险一金", f"{annual_employer:.2f} 元"),
            ("年度工资个税", f"{annual_salary_tax:.2f} 元"),
            ("年终奖", f"{bonus:.2f} 元"),
            ("年终奖个税（单独计税）", f"{bonus_tax:.2f} 元"),
            ("年度总个税", f"{total_tax:.2f} 元"),
            ("年度到手收入", f"{total_net:.2f} 元"),
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