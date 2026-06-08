"""计算器插件 - 简易科学计算器"""

import sys
import os
import math

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLineEdit, QLabel, QSizePolicy,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

# 动态添加项目根目录到 sys.path
_project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.core.plugin_base import PluginBase


class CalculatorWidget(PluginBase):
    """计算器插件"""

    plugin_id = "calculator"
    plugin_name = "计算器"
    plugin_version = "1.0.0"
    plugin_description = "简易科学计算器，支持基础四则运算和常用数学函数"
    plugin_icon = "fa5s.calculator"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)

        # 显示屏
        self.display = QLineEdit("0")
        self.display.setAlignment(Qt.AlignRight)
        self.display.setFont(QFont("", 24))
        self.display.setReadOnly(True)
        self.display.setMinimumHeight(60)
        self.display.setStyleSheet("""
            QLineEdit {
                background: #2d2d2d;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
            }
        """)
        layout.addWidget(self.display)

        # 历史记录标签
        self.history_label = QLabel("")
        self.history_label.setAlignment(Qt.AlignRight)
        self.history_label.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(self.history_label)

        # 按钮网格
        grid = QGridLayout()
        grid.setSpacing(6)

        buttons = [
            # (text, row, col, rowspan, colspan, style)
            ("C", 0, 0, 1, 1, "func"),
            ("⌫", 0, 1, 1, 1, "func"),
            ("(", 0, 2, 1, 1, "func"),
            (")", 0, 3, 1, 1, "func"),
            ("7", 1, 0, 1, 1, "num"),
            ("8", 1, 1, 1, 1, "num"),
            ("9", 1, 2, 1, 1, "num"),
            ("÷", 1, 3, 1, 1, "op"),
            ("4", 2, 0, 1, 1, "num"),
            ("5", 2, 1, 1, 1, "num"),
            ("6", 2, 2, 1, 1, "num"),
            ("×", 2, 3, 1, 1, "op"),
            ("1", 3, 0, 1, 1, "num"),
            ("2", 3, 1, 1, 1, "num"),
            ("3", 3, 2, 1, 1, "num"),
            ("−", 3, 3, 1, 1, "op"),
            ("0", 4, 0, 1, 1, "num"),
            (".", 4, 1, 1, 1, "num"),
            ("=", 4, 2, 1, 2, "eq"),
            ("+", 0, 4, 1, 1, "op"),
            ("√", 1, 4, 1, 1, "func"),
            ("%", 2, 4, 1, 1, "func"),
            ("±", 3, 4, 1, 1, "func"),
            ("π", 4, 4, 1, 1, "func"),
        ]

        styles = {
            "num": """
                QPushButton {
                    background: #f5f5f5; border: none; border-radius: 8px;
                    font-size: 18px; padding: 12px;
                }
                QPushButton:hover { background: #e0e0e0; }
                QPushButton:pressed { background: #d0d0d0; }
            """,
            "op": """
                QPushButton {
                    background: #4a90d9; color: white; border: none;
                    border-radius: 8px; font-size: 18px; padding: 12px;
                }
                QPushButton:hover { background: #357abd; }
                QPushButton:pressed { background: #2a6aad; }
            """,
            "func": """
                QPushButton {
                    background: #e8e8e8; border: none; border-radius: 8px;
                    font-size: 16px; padding: 12px;
                }
                QPushButton:hover { background: #d8d8d8; }
                QPushButton:pressed { background: #c8c8c8; }
            """,
            "eq": """
                QPushButton {
                    background: #34c759; color: white; border: none;
                    border-radius: 8px; font-size: 20px; padding: 12px;
                }
                QPushButton:hover { background: #2ab74a; }
                QPushButton:pressed { background: #1fa73a; }
            """,
        }

        for text, row, col, rs, cs, style_type in buttons:
            btn = QPushButton(text)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setMinimumHeight(44)
            btn.setStyleSheet(styles[style_type])
            btn.clicked.connect(lambda checked, t=text: self._on_button(t))
            grid.addWidget(btn, row, col, rs, cs)

        layout.addLayout(grid)

        # 状态
        self._expression = ""
        self._new_input = True

    def _on_button(self, text: str):
        if text == "C":
            self._clear()
        elif text == "⌫":
            self._backspace()
        elif text == "=":
            self._calculate()
        elif text == "±":
            self._negate()
        elif text == "√":
            self._square_root()
        elif text == "%":
            self._percent()
        elif text == "π":
            self._insert_pi()
        else:
            self._append(text)

    def _clear(self):
        self.display.setText("0")
        self._expression = ""
        self._new_input = True
        self.history_label.setText("")

    def _backspace(self):
        current = self.display.text()
        if len(current) > 1:
            self.display.setText(current[:-1])
        else:
            self.display.setText("0")
            self._new_input = True

    def _append(self, text: str):
        # 替换运算符为 Python 可识别的
        op_map = {"÷": "/", "×": "*", "−": "-"}
        actual = op_map.get(text, text)

        if self._new_input and text not in "+-×÷*/":
            self._expression = ""
            self._new_input = False

        current = self.display.text()
        if current == "0" and text not in "+-×÷*/.":
            self.display.setText(text)
            self._expression = actual
        else:
            self.display.setText(current + text)
            self._expression += actual

    def _calculate(self):
        try:
            expr = self._expression
            # 安全评估 - 仅允许数学表达式
            allowed = set("0123456789+-*/.() ")
            if not all(c in allowed for c in expr):
                self.display.setText("错误")
                return

            result = eval(expr)
            if isinstance(result, float) and result == int(result):
                result = int(result)

            self.history_label.setText(f"{self.display.text()} =")
            self.display.setText(str(result))
            self._expression = str(result)
            self._new_input = True
        except ZeroDivisionError:
            self.display.setText("除数不能为零")
            self._new_input = True
        except Exception:
            self.display.setText("表达式错误")
            self._new_input = True

    def _negate(self):
        current = self.display.text()
        try:
            val = float(current)
            val = -val
            if val == int(val):
                val = int(val)
            self.display.setText(str(val))
            self._expression = str(val)
        except ValueError:
            pass

    def _square_root(self):
        try:
            val = float(self.display.text())
            if val < 0:
                self.display.setText("无效输入")
                return
            result = math.sqrt(val)
            if result == int(result):
                result = int(result)
            else:
                result = round(result, 8)
            self.history_label.setText(f"√{val} =")
            self.display.setText(str(result))
            self._expression = str(result)
            self._new_input = True
        except ValueError:
            self.display.setText("错误")

    def _percent(self):
        try:
            val = float(self.display.text())
            result = val / 100
            self.display.setText(str(result))
            self._expression = str(result)
            self._new_input = True
        except ValueError:
            pass

    def _insert_pi(self):
        self.display.setText(str(math.pi))
        self._expression = str(math.pi)
        self._new_input = True