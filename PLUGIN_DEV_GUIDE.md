# Treas 插件开发指南

本文档面向第三方开发者，详细说明如何为 Treas 淼淼百宝箱开发、测试和分享插件。

---

## 目录

1. [快速开始](#1-快速开始)
2. [插件目录结构](#2-插件目录结构)
3. [plugin.json 完整规范](#3-pluginjson-完整规范)
4. [widget.py 开发指南](#4-widgetpy-开发指南)
5. [可用图标列表](#5-可用图标列表)
6. [依赖管理](#6-依赖管理)
7. [插件数据库](#7-插件数据库)
8. [插件分享流程](#8-插件分享流程)
9. [最佳实践](#9-最佳实践)
10. [完整示例](#10-完整示例带第三方依赖)
11. [常见问题](#11-常见问题)

---

## 1. 快速开始

只需 **2 个文件** 即可创建一个 Treas 插件：

### 第一步：创建插件目录

在 Treas 项目的 `plugins/` 目录下创建一个新文件夹（**不要放在** `src/plugins/`，那是内置插件目录）：

```
plugins/
└── my_hello/
    ├── plugin.json    # 插件描述清单（必需）
    └── widget.py      # 插件 UI 实现（必需）
```

### 第二步：编写 plugin.json

```json
{
    "id": "my_hello",
    "name": "你好世界",
    "version": "1.0.0",
    "description": "我的第一个 Treas 插件",
    "icon": "APPLICATION",
    "entry": "widget.py",
    "entry_class": "HelloWidget",
    "window_size": [400, 300],
    "author": "你的名字"
}
```

### 第三步：编写 widget.py

```python
import sys
import os

# 动态添加项目根目录到 sys.path（必需）
_project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from PyQt5.QtWidgets import QVBoxLayout, QLabel
from src.core.plugin_base import PluginBase


class HelloWidget(PluginBase):
    """你好世界插件"""

    plugin_id = "my_hello"
    plugin_name = "你好世界"
    plugin_version = "1.0.0"
    plugin_description = "我的第一个 Treas 插件"
    plugin_icon = "APPLICATION"

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        label = QLabel("你好，Treas！")
        label.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(label)
```

### 第四步：启动应用验证

```bash
python -m src.main
```

启动后在「全部工具」页面即可看到你的插件。

---

## 2. 插件目录结构

### 最小结构（必需文件）

```
plugins/my_tool/
├── plugin.json    # 插件描述清单
└── widget.py      # 插件 UI 实现
```

### 完整结构（含可选文件）

```
plugins/my_tool/
├── plugin.json        # 插件描述清单（必需）
├── widget.py          # 插件 UI 实现（必需）
├── requirements.txt   # 依赖声明（可选，与 plugin.json 的 dependencies 二选一）
├── README.md          # 插件说明文档（可选）
├── assets/            # 资源文件（可选）
│   ├── icons/
│   └── data/
└── helpers.py         # 辅助模块（可选）
```

> **注意**：导出插件时，目录内的**所有文件**都会被打包到 zip 中。

---

## 3. plugin.json 完整规范

`plugin.json` 是插件的描述清单，Treas 通过它识别和加载插件。

### 字段说明

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `id` | string | ✅ | — | 插件唯一标识符。只能包含小写字母、数字和下划线，如 `"currency_converter"` |
| `name` | string | ✅ | — | 插件显示名称，如 `"汇率换算"` |
| `version` | string | ✅ | `"1.0.0"` | 语义化版本号 |
| `description` | string | ✅ | — | 一句话描述插件功能 |
| `icon` | string | ❌ | `"APPLICATION"` | 图标名称，见[可用图标列表](#5-可用图标列表) |
| `category` | string | ❌ | `""` | 建议分类名称。用户导入后可自行调整 |
| `entry` | string | ❌ | `"widget.py"` | 入口 Python 文件名 |
| `entry_class` | string | ❌ | `"PluginWidget"` | 入口文件中的插件类名 |
| `window_size` | [int, int] | ❌ | `[700, 700]` | 窗口尺寸 `[宽, 高]`。宽度 ≤ 400 时为紧凑模式（无滚动条） |
| `author` | string | ❌ | `""` | 作者名称 |
| `dependencies` | string[] | ❌ | `[]` | pip 依赖列表，如 `["requests>=2.28", "beautifulsoup4"]` |

### 示例

```json
{
    "id": "stock_tracker",
    "name": "股票追踪",
    "version": "1.2.0",
    "description": "实时查看股票行情，支持自选股管理",
    "icon": "GLOBE",
    "category": "投资工具",
    "entry": "widget.py",
    "entry_class": "StockTrackerWidget",
    "window_size": [500, 600],
    "author": "张三",
    "dependencies": ["requests>=2.28", "pandas>=1.5"]
}
```

### id 命名规范

- 只使用 **小写字母**、**数字** 和 **下划线**
- 推荐格式：`功能_类型`，如 `mortgage_calculator`、`expense_tracker`
- 全局唯一，避免与已有插件冲突

---

## 4. widget.py 开发指南

### 插件基类

所有插件必须继承 `PluginBase`：

```python
from src.core.plugin_base import PluginBase

class MyWidget(PluginBase):
    plugin_id = "my_tool"           # 与 plugin.json 的 id 一致
    plugin_name = "我的工具"         # 与 plugin.json 的 name 一致
    plugin_version = "1.0.0"        # 与 plugin.json 的 version 一致
    plugin_description = "描述"     # 与 plugin.json 的 description 一致
    plugin_icon = "APPLICATION"     # 与 plugin.json 的 icon 一致
```

### 生命周期

```python
class MyWidget(PluginBase):
    def __init__(self, parent=None):
        """插件创建时调用 - 初始化 UI"""
        super().__init__(parent)
        self._init_ui()

    def on_activate(self):
        """插件窗口打开时调用 - 可用于刷新数据"""
        super().on_activate()
        self._refresh_data()

    def on_deactivate(self):
        """插件窗口关闭时调用 - 可用于保存状态、停止定时器"""
        super().on_deactivate()
        self._save_state()
```

### sys.path 设置（必需）

插件 `widget.py` 的**最开头**必须包含以下代码，确保能导入 Treas 核心模块：

```python
import sys
import os

_project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
```

> 如果插件位于 `plugins/my_tool/`，则向上两级到达项目根目录。
> 如果插件位于 `src/plugins/my_tool/`（内置插件），则向上三级。

### UI 编写

插件本质上是一个 **PyQt5 QWidget**，你可以使用任何 PyQt5 组件：

```python
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor

class MyWidget(PluginBase):
    # ...

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)

        # 标题
        title = QLabel("我的工具")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # 输入框
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("请输入...")
        layout.addWidget(self.input_field)

        # 按钮
        btn = QPushButton("执行")
        btn.clicked.connect(self._on_click)
        layout.addWidget(btn)

    def _on_click(self):
        text = self.input_field.text()
        # 处理逻辑...
```

### 使用 QFluentWidgets 组件（推荐）

Treas 内置了 [PyQt-Fluent-Widgets](https://qfluentwidgets.com/)，你可以直接使用其 Fluent 风格组件：

```python
from qfluentwidgets import (
    PushButton, PrimaryPushButton,
    LineEdit, TextEdit,
    ComboBox, SpinBox,
    CardWidget, StrongBodyLabel, CaptionLabel,
    InfoBar, InfoBarPosition,
    FluentIcon,
)

# 使用 Fluent 风格按钮
btn = PrimaryPushButton("计算")
input_field = LineEdit()
input_field.setPlaceholderText("请输入金额...")
```

### 窗口尺寸建议

| 场景 | 建议尺寸 | 说明 |
|------|----------|------|
| 简单工具 | `[340, 500]` | 紧凑窗口，无滚动条 |
| 中等工具 | `[500, 600]` | 带滚动条 |
| 复杂工具 | `[700, 700]` | 默认尺寸，带滚动条 |

---

## 5. 可用图标列表

在 `plugin.json` 的 `icon` 字段中使用以下图标名称：

### 常用图标

| 图标名称 | 说明 |
|----------|------|
| `APPLICATION` | 应用（默认） |
| `CALCULATOR` | 计算器 |
| `GLOBE` | 全球/网络 |
| `SYNC` | 同步/转换 |
| `LIBRARY` | 库/存储 |
| `FOLDER` | 文件夹 |
| `HEART` | 收藏 |
| `PEOPLE` | 用户/人员 |
| `MAIL` | 邮件 |
| `SHOPPING_CART` | 购物 |
| `PIN` | 置顶 |
| `TAG` | 标签 |
| `SEARCH` | 搜索 |
| `EDIT` | 编辑 |
| `SAVE` | 保存 |
| `DELETE` | 删除 |
| `GAME` | 游戏 |
| `PHOTO` | 照片 |
| `MUSIC` | 音乐 |
| `VIDEO` | 视频 |
| `BOOK_SHELF` | 书架 |
| `CALENDAR` | 日历 |
| `CHART` | 图表 |
| `CLOCK` | 时钟 |
| `COIN` | 硬币 |
| `COMPASS` | 指南针 |
| `DICTIONARY` | 字典 |
| `DOCUMENT` | 文档 |
| `DOWNLOAD` | 下载 |
| `HOME` | 主页 |
| `LINK` | 链接 |
| `MARKET` | 市场 |
| `MOBILE` | 手机 |
| `SETTING` | 设置 |
| `STAR` | 星标 |
| `UPDATE` | 更新 |
| `ZIP` | 压缩包 |

> 完整列表请参考 [FluentIcon 枚举](https://qfluentwidgets.com/zh-cn/components/icon)。
> 如果你使用的名称不存在，会自动回退为 `APPLICATION`。

---

## 6. 依赖管理

### 声明依赖

在 `plugin.json` 中使用 `dependencies` 字段声明 pip 依赖：

```json
{
    "id": "http_tool",
    "name": "HTTP 测试工具",
    "dependencies": ["requests>=2.28", "beautifulsoup4"]
}
```

依赖声明格式与 `requirements.txt` 一致，支持以下版本操作符：

| 操作符 | 示例 | 说明 |
|--------|------|------|
| （无） | `"requests"` | 最新版本 |
| `>=` | `"requests>=2.28"` | 大于等于 |
| `==` | `"flask==2.3.0"` | 精确版本 |
| `<=` | `"django<=4.2"` | 小于等于 |
| `>` | `"numpy>1.24"` | 大于 |
| `<` | `"pillow<10.0"` | 小于 |
| `~=` | `"django~=4.2.0"` | 兼容版本 |

### 依赖安装流程

1. 用户导入插件后，Treas 自动检测依赖状态
2. 如果依赖缺失，工具卡片显示 ⚠️ 警告和缺失的包名
3. 「打开」按钮被禁用
4. 用户点击「安装依赖」按钮后，Treas 在后台通过 `pip install` 自动下载安装
5. 安装完成后插件即可正常使用

### 已内置的库

以下库随 Treas 一起安装，**无需** 在 dependencies 中声明：

- PyQt5
- qfluentwidgets (PyQt-Fluent-Widgets)
- packaging
- Python 标准库（math, json, sqlite3, os, sys, re 等）

### 依赖安装位置

第三方依赖安装在 Treas 数据目录的 `.site-packages/` 中，不会污染系统 Python 环境：

| 平台 | 路径 |
|------|------|
| macOS | `~/Library/Application Support/Treas/.site-packages/` |
| Windows | `%LOCALAPPDATA%/Treas/.site-packages/` |
| Linux | `~/.local/share/Treas/.site-packages/` |

---

## 7. 插件数据库

自定义插件可以使用专属的 SQLite 数据库来存储数据。内置插件使用公共数据库（`Database` 单例）。

### 基本配置

在 `plugin.json` 中添加 `database` 字段即可启用：

```json
{
    "id": "my_expense",
    "name": "记账本",
    "database": {
        "init_sql": "init.sql",
        "version": 1
    }
}
```

### database 字段说明

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `init_sql` | string | ❌ | `null` | SQL 初始化文件路径（相对于插件目录），首次加载时自动执行 |
| `version` | int | ❌ | `1` | 数据库版本号，用于版本迁移 |
| `shared_group` | string | ❌ | `null` | 共享组名。设置后，同组插件共用一个数据库文件 |

### 独立数据库（默认）

不设置 `shared_group` 时，每个插件使用独立的数据库文件：

```
data/plugin_data/
├── my_expense.db        # 独立数据库
├── my_notes.db          # 独立数据库
└── group_finance.db     # 共享数据库（见下文）
```

### 共享数据库

多个插件声明相同的 `shared_group` 时，共用一个数据库文件：

```json
// 插件 A: plugin.json
{ "id": "stock_tracker", "database": { "shared_group": "finance" } }

// 插件 B: plugin.json
{ "id": "fund_tracker", "database": { "shared_group": "finance" } }
```

两个插件都会使用 `data/plugin_data/group_finance.db`。

### 在代码中使用数据库

```python
class MyWidget(PluginBase):
    plugin_id = "my_expense"

    def on_activate(self):
        super().on_activate()
        self._load_data()

    def _load_data(self):
        """读取数据"""
        db = self.get_db()
        try:
            rows = db.execute("SELECT * FROM records ORDER BY date DESC").fetchall()
            for row in rows:
                # 处理数据...
                pass
        finally:
            db.close()

    def _add_record(self, amount, category):
        """写入数据"""
        db = self.get_db()
        try:
            db.execute(
                "INSERT INTO records (amount, category, date) VALUES (?, ?, datetime('now'))",
                (amount, category)
            )
            db.commit()
        finally:
            db.close()
```

### SQL 初始化文件

创建 `init.sql` 文件定义表结构：

```sql
-- init.sql
CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    note TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_records_date ON records(date);
```

首次加载插件时，Treas 自动执行此文件创建表。

### 数据库版本迁移

当 `version` 增大时，可覆盖 `on_db_upgrade` 方法执行迁移：

```python
class MyWidget(PluginBase):
    plugin_id = "my_expense"

    def on_db_upgrade(self, old_version: int, new_version: int):
        """数据库版本迁移"""
        db = self.get_db()
        try:
            if old_version < 2:
                # v1 → v2: 添加 note 字段
                db.execute("ALTER TABLE records ADD COLUMN note TEXT DEFAULT ''")
            if old_version < 3:
                # v2 → v3: 添加标签表
                db.execute("""
                    CREATE TABLE IF NOT EXISTS tags (
                        id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE
                    )
                """)
            db.commit()
        finally:
            db.close()
```

### 卸载时的数据处理

用户删除自定义插件时，Treas 会弹出选项：
- **保留数据并删除** — 仅删除插件文件，数据库文件保留（方便重新安装后恢复数据）
- **彻底删除** — 同时删除数据库文件

### 注意事项

- **内置插件**使用公共 `Database` 单例，不适用此机制
- `get_db()` 每次返回**新的连接**，使用完毕后务必 `db.close()`
- 未配置 `database` 字段的插件调用 `self.get_db()` 会抛出 `RuntimeError`

---

## 8. 插件分享流程

### 导出插件

1. 在 Treas 主界面，点击工具卡片上的 **「分享」** 按钮（📤）
2. 插件自动打包为 `.zip` 文件，保存在 `exported/` 目录
3. zip 文件名格式：`{plugin_id}_v{version}.zip`
4. zip 中**自动包含** `requirements.txt`（基于 `dependencies` 字段生成）

### 导出的 zip 包结构

```
my_tool_v1.0.0.zip
├── plugin.json
├── widget.py
├── helpers.py          # 如果有的话
├── assets/             # 如果有的话
│   └── data.csv
└── requirements.txt    # 自动生成
```

### 导入插件

1. 将 zip 文件发送给其他用户
2. 在 Treas 主界面点击 **「导入插件」** 按钮
3. 选择 zip 文件，导入完成
4. 可选择将插件归类到某个分类

### 分享注意事项

- zip 包中**不要包含** `.pyc`、`__pycache__`、`.git` 等文件
- 确保所有依赖都在 `dependencies` 中声明
- 如果插件读取本地文件，使用相对路径（基于插件目录）

---

## 9. 最佳实践

### 命名规范

```
插件 ID:      小写 + 下划线，如 mortgage_calculator
插件名称:     简洁中文，如 房贷计算器
类名:         PascalCase + Widget 后缀，如 MortgageCalculatorWidget
文件名:       小写 + 下划线，如 mortgage_calculator/
```

### 样式建议

```python
# 推荐：使用 QFluentWidgets 组件（风格统一）
from qfluentwidgets import PushButton, LineEdit
btn = PushButton("计算")

# 也可：使用自定义 QSS 样式
btn.setStyleSheet("""
    QPushButton {
        background: #4a90d9;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
    }
    QPushButton:hover { background: #357abd; }
""")
```

### 数据存储

插件的数据应存储在插件自身目录中：

```python
import os

# 获取插件目录
plugin_dir = os.path.dirname(os.path.abspath(__file__))
data_file = os.path.join(plugin_dir, "data", "my_data.db")

# 或使用 Treas 数据目录（适合用户数据）
from src.core.paths import get_app_data_dir
app_data = get_app_data_dir()
```

### 错误处理

```python
def _calculate(self):
    try:
        result = self._do_calculation()
        self.result_label.setText(str(result))
    except ZeroDivisionError:
        self.result_label.setText("错误：除数不能为零")
    except ValueError as e:
        self.result_label.setText(f"输入错误: {e}")
    except Exception as e:
        self.result_label.setText(f"计算出错: {e}")
```

### 调试技巧

```python
# 在 widget.py 中使用 print 输出调试信息
print(f"[MyPlugin] 调试信息: {value}")

# 日志会输出到终端（开发模式）
# python -m src.main
```

---

## 10. 完整示例（带第三方依赖）

以下是一个完整的 HTTP 请求测试工具插件：

### plugin.json

```json
{
    "id": "http_tester",
    "name": "HTTP 请求测试",
    "version": "1.0.0",
    "description": "发送 HTTP 请求并查看响应，支持 GET/POST",
    "icon": "GLOBE",
    "category": "开发工具",
    "entry": "widget.py",
    "entry_class": "HttpTesterWidget",
    "window_size": [500, 600],
    "author": "开发者",
    "dependencies": ["requests>=2.28"]
}
```

### widget.py

```python
"""HTTP 请求测试插件"""

import sys
import os
import json

# 设置项目根目录到 sys.path（必需）
_project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QTextEdit, QComboBox,
    QSizePolicy,
)
from PyQt5.QtCore import Qt

from qfluentwidgets import (
    PushButton, PrimaryPushButton, LineEdit,
    ComboBox, TextEdit, StrongBodyLabel, CaptionLabel,
)

from src.core.plugin_base import PluginBase


class HttpTesterWidget(PluginBase):
    """HTTP 请求测试插件"""

    plugin_id = "http_tester"
    plugin_name = "HTTP 请求测试"
    plugin_version = "1.0.0"
    plugin_description = "发送 HTTP 请求并查看响应"
    plugin_icon = "GLOBE"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # 标题
        title = StrongBodyLabel("HTTP 请求测试")
        title.setStyleSheet("font-size: 16px;")
        layout.addWidget(title)

        # URL 输入行
        url_layout = QHBoxLayout()

        self.method_combo = ComboBox()
        self.method_combo.addItems(["GET", "POST", "PUT", "DELETE"])
        self.method_combo.setFixedWidth(100)
        url_layout.addWidget(self.method_combo)

        self.url_input = LineEdit()
        self.url_input.setPlaceholderText("输入 URL，如 https://httpbin.org/get")
        url_layout.addWidget(self.url_input)

        send_btn = PrimaryPushButton("发送")
        send_btn.clicked.connect(self._send_request)
        url_layout.addWidget(send_btn)

        layout.addLayout(url_layout)

        # 请求体（POST 用）
        layout.addWidget(CaptionLabel("请求体 (JSON):"))
        self.body_input = TextEdit()
        self.body_input.setFixedHeight(100)
        self.body_input.setPlaceholderText('{"key": "value"}')
        layout.addWidget(self.body_input)

        # 响应区域
        layout.addWidget(StrongBodyLabel("响应:"))
        self.response_output = TextEdit()
        self.response_output.setReadOnly(True)
        self.response_output.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        layout.addWidget(self.response_output)

    def _send_request(self):
        """发送 HTTP 请求"""
        import requests

        method = self.method_combo.currentText()
        url = self.url_input.text().strip()

        if not url:
            self.response_output.setText("请输入 URL")
            return

        try:
            self.response_output.setText("请求中...")

            kwargs = {"timeout": 10}

            if method in ("POST", "PUT"):
                body = self.body_input.toPlainText().strip()
                if body:
                    kwargs["json"] = json.loads(body)

            response = getattr(requests, method.lower())(url, **kwargs)

            result = (
                f"状态码: {response.status_code}\n"
                f"耗时: {response.elapsed.total_seconds():.2f}s\n"
                f"{'─' * 40}\n"
                f"{json.dumps(response.json(), indent=2, ensure_ascii=False)}"
            )
            self.response_output.setText(result)

        except json.JSONDecodeError:
            self.response_output.setText(response.text)
        except requests.exceptions.Timeout:
            self.response_output.setText("请求超时")
        except Exception as e:
            self.response_output.setText(f"请求失败: {e}")
```

---

## 11. 常见问题

### Q: 插件没有出现在列表中？

检查以下几点：
1. `plugin.json` 是否存在且格式正确（JSON 语法）
2. `plugin.json` 中 `id` 字段是否已填写
3. 插件目录是否在 `plugins/` 或 `src/plugins/` 下
4. `entry` 指定的文件是否存在

### Q: 导入插件后显示「缺少依赖」？

这是正常的。在插件卡片上点击「安装依赖」按钮，Treas 会自动下载安装所需的 pip 包。

### Q: 插件加载失败，控制台报错？

1. 确认 `widget.py` 开头有 `sys.path` 设置代码
2. 检查类名是否与 `plugin.json` 的 `entry_class` 一致
3. 检查类是否继承了 `PluginBase`
4. 在终端运行 `python -m src.main` 查看完整错误信息

### Q: 如何在插件中使用 SQLite 数据库？

```python
import sqlite3
import os

# 方式 1：在插件目录中创建数据库
plugin_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(plugin_dir, "my_data.db")

conn = sqlite3.connect(db_path)
# ...

# 方式 2：使用 Treas 数据目录
from src.core.paths import get_app_data_dir
db_path = os.path.join(get_app_data_dir(), "my_tool_data.db")
conn = sqlite3.connect(db_path)
```

### Q: 如何在插件间共享数据？

使用 Treas 的 `Database` 单例：

```python
from src.core.database import Database

db = Database()
db.execute(
    "CREATE TABLE IF NOT EXISTS my_data (key TEXT, value TEXT)"
)
```

### Q: 支持哪些 Python 版本？

Python 3.9+

### Q: 插件可以使用第三方 Qt 组件吗？

可以，只要在 `dependencies` 中声明即可。但推荐优先使用 PyQt5 和 QFluentWidgets 内置组件，以保持风格一致。

---

## 附录：插件开发检查清单

- [ ] `plugin.json` 格式正确，`id` 唯一
- [ ] `widget.py` 包含 `sys.path` 设置代码
- [ ] 插件类继承了 `PluginBase`
- [ ] 类名与 `entry_class` 一致
- [ ] 第三方依赖已在 `dependencies` 中声明
- [ ] 窗口尺寸 `window_size` 设置合理
- [ ] 错误处理完善（网络请求、文件操作等）
- [ ] 使用相对路径引用资源文件
- [ ] 不包含 `.pyc`、`__pycache__`、`.git` 等文件
- [ ] 已在 Treas 中测试导入/导出流程