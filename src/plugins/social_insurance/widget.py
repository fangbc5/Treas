"""五险一金计算器 - 计算社保、公积金、个税及年终奖"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QHeaderView, QWidget,
)
from PyQt5.QtGui import QFont

from qfluentwidgets import (
    CardWidget, StrongBodyLabel, BodyLabel, CaptionLabel,
    LineEdit, ComboBox, PushButton, PrimaryPushButton,
    TableWidget, HeaderCardWidget, SpinBox,
)

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

        # ========== 输入区 ==========
        input_card = HeaderCardWidget(self)
        input_card.setTitle("输入信息")

        input_layout = QGridLayout()
        input_layout.setSpacing(12)
        input_layout.setContentsMargins(20, 16, 20, 16)

        # 税前月薪
        input_layout.addWidget(StrongBodyLabel("税前月薪（元）"), 0, 0)
        self.salary_input = SpinBox()
        self.salary_input.setRange(0, 9999999)
        self.salary_input.setValue(10000)
        self.salary_input.setSingleStep(1000)
        self.salary_input.suffix = " 元"
        input_layout.addWidget(self.salary_input, 0, 1)

        # 年终奖
        input_layout.addWidget(StrongBodyLabel("年终奖（元）"), 1, 0)
        self.bonus_input = SpinBox()
        self.bonus_input.setRange(0, 9999999)
        self.bonus_input.setValue(0)
        self.bonus_input.setSingleStep(1000)
        self.bonus_input.suffix = " 元"
        input_layout.addWidget(self.bonus_input, 1, 1)

        # 公积金比例
        input_layout.addWidget(StrongBodyLabel("住房公积金比例"), 2, 0)
        self.fund_ratio = ComboBox()
        self.fund_ratio.addItems(
            ["5%", "6%", "7%", "8%", "9%", "10%", "11%", "12%"]
        )
        self.fund_ratio.setCurrentIndex(6)  # 默认 12%，index=7；改 7%
        input_layout.addWidget(self.fund_ratio, 2, 1)

        # 计算按钮
        calc_btn = PrimaryPushButton("开始计算")
        calc_btn.clicked.connect(self._calculate)
        input_layout.addWidget(calc_btn, 3, 0, 1, 2)

        input_card.viewLayout().addLayout(input_layout)
        layout.addWidget(input_card)

        # ========== 月度五险一金明细 ==========
        self.insurance_card = HeaderCardWidget(self)
        self.insurance_card.setTitle("月度五险一金明细")
        self.insurance_table = self._create_table(
            ["项目", "个人比例", "个人金额", "单位比例", "单位金额"]
        )
        self.insurance_card.viewLayout().addWidget(self.insurance_table)
        layout.addWidget(self.insurance_card)

        # ========== 个税与年终奖 ==========
        self.tax_card = HeaderCardWidget(self)
        self.tax_card.setTitle("个税计算")
        self.tax_layout = QVBoxLayout()
        self.tax_layout.setSpacing(8)
        self.tax_card.viewLayout().addLayout(self.tax_layout)
        layout.addWidget(self.tax_card)

        # ========== 年度汇总 ==========
        self.summary_card = HeaderCardWidget(self)
        self.summary_card.setTitle("年度汇总")
        self.summary_layout = QGridLayout()
        self.summary_layout.setSpacing(8)
        self.summary_card.viewLayout().addLayout(self.summary_layout)
        layout.addWidget(self.summary_card)

        layout.addStretch()

        # 默认计算一次
        self._calculate()

    def _create_table(self, headers: list) -> TableWidget:
        table = TableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        table.setEditTriggers(table.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.setMaximumHeight(250)
        return table

    def _calculate(self):
        salary = self.salary_input.value()
        bonus = self.bonus_input.value()
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

        # 计算五险一金明细
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

        # 合计行
        rows.append((
            "合计",
            "-",
            f"{personal_total:.2f}",
            "-",
            f"{employer_total:.2f}",
        ))

        # 更新五险一金表格
        self.insurance_table.setRowCount(len(rows))
        for r, row_data in enumerate(rows):
            for c, text in enumerate(row_data):
                item = self.insurance_table.item(r, c)
                if item is None:
                    from PyQt5.QtWidgets import QTableWidgetItem
                    item = QTableWidgetItem(text)
                    item.setTextAlignment(Qt.AlignCenter)
                    self.insurance_table.setItem(r, c, item)
                else:
                    item.setText(text)

        # 最后一行加粗
        for c in range(5):
            item = self.insurance_table.item(len(rows)-1, c)
            if item:
                font = item.font()
                font.setBold(True)
                item.setFont(font)

        # ===== 月度工资个税 =====
        monthly_taxable = salary - personal_total - 5000
        monthly_tax = calc_tax(monthly_taxable * 12) / 12  # 年累计除以12
        monthly_after_tax = salary - personal_total - monthly_tax

        # ===== 年终奖单独计税 =====
        if bonus > 0:
            monthly_bonus = bonus / 12
            bonus_tax = calc_tax(monthly_bonus * 12)  # 复用税率表
            # 实际年终奖单独计税是: 找月均对应的税率档，然后 bonus * rate - deduction
            for upper, rate, deduction in TAX_BRACKETS:
                if monthly_bonus <= upper:
                    bonus_tax = bonus * rate - deduction
                    break
        else:
            bonus_tax = 0.0

        bonus_after_tax = bonus - bonus_tax

        # 更新个税区域
        # 清除旧内容
        while self.tax_layout.count():
            item = self.tax_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.tax_layout.addWidget(self._kv_label(
            "月度应纳税所得额", f"{monthly_taxable:.2f} 元"
        ))
        self.tax_layout.addWidget(self._kv_label(
            "月度工资个税", f"{monthly_tax:.2f} 元"
        ))
        self.tax_layout.addWidget(self._kv_label(
            "月度税后工资", f"{monthly_after_tax:.2f} 元"
        ))
        self.tax_layout.addWidget(self._h_separator())
        self.tax_layout.addWidget(self._kv_label(
            "年终奖", f"{bonus:.2f} 元"
        ))
        self.tax_layout.addWidget(self._kv_label(
            "年终奖个税（单独计税）", f"{bonus_tax:.2f} 元"
        ))
        self.tax_layout.addWidget(self._kv_label(
            "年终奖税后金额", f"{bonus_after_tax:.2f} 元"
        ))

        # ===== 年度汇总 =====
        annual_gross = salary * 12 + bonus
        annual_personal = personal_total * 12
        annual_employer = employer_total * 12
        annual_tax = monthly_tax * 12 + bonus_tax
        annual_net = monthly_after_tax * 12 + bonus_after_tax

        # 清除旧内容
        while self.summary_layout.count():
            item = self.summary_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

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

        for i, (label, value) in enumerate(summary_items):
            lbl = BodyLabel(label)
            val = StrongBodyLabel(value)
            val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.summary_layout.addWidget(lbl, i, 0)
            self.summary_layout.addWidget(val, i, 1)

    def _kv_label(self, key: str, value: str) -> QWidget:
        """创建一行 key-value 显示"""
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 2, 0, 2)
        h.addWidget(BodyLabel(key))
        h.addStretch()
        val = StrongBodyLabel(value)
        val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        h.addWidget(val)
        return w

    @staticmethod
    def _h_separator() -> QWidget:
        """水平分隔线"""
        line = QLabel()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #e0e0e0; margin: 4px 0;")
        return line