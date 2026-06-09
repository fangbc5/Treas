# Treas - 淼淼百宝箱

一个基于 PyQt5 + PyQt-Fluent-Widgets 的插件式财务小工具箱平台，支持工具分类管理、插件动态加载和分享。

## 功能特性

- 🗂️ **分类管理** — 对工具进行分类组织，支持增删改查和图标选择
- 🧩 **插件系统** — 每个工具是独立插件，遵循统一接口，动态加载
- 📤 **分享机制** — 工具可打包导出为 zip，他人导入即可使用
- 🎨 **Fluent UI** — 基于 QFluentWidgets 的 Windows 11 风格现代界面
- 💾 **本地存储** — SQLite 数据库，数据保存在用户数据目录，支持 macOS / Windows / Linux

## 内置工具

| 工具 | 分类 | 说明 |
|------|------|------|
| 🧮 计算器 | 计算工具 | 简易科学计算器，支持四则运算和数学函数 |
| 💱 汇率换算 | 转换工具 | 常用货币汇率换算，支持15种货币 |
| 📒 简易记账本 | 记账工具 | 轻量级收支记录，支持添加、删除、统计 |

## 快速开始

```bash
# 1. 克隆项目
git clone <repo-url>
cd Treas

# 2. 运行启动脚本（自动创建虚拟环境并安装依赖）
chmod +x run.sh
./run.sh
```

或手动运行：

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动应用
python -m src.main
```

## 项目结构

```
Treas/
├── requirements.txt          # 依赖清单
├── run.sh                    # 启动脚本
├── README.md                 # 项目说明
├── src/
│   ├── main.py               # 应用入口
│   ├── core/                 # 核心框架
│   │   ├── database.py       # 数据库管理 (SQLite)
│   │   ├── plugin_base.py    # 插件基类
│   │   ├── plugin_manager.py # 插件管理器
│   │   ├── category_manager.py # 分类管理
│   │   └── share_manager.py  # 导入/导出/分享
│   ├── views/                # UI 视图层 (Fluent 风格)
│   │   ├── main_window.py    # 主窗口 (FluentWindow)
│   │   ├── tool_card.py      # 工具卡片 (CardWidget)
│   │   ├── category_dialog.py # 分类对话框
│   │   └── plugin_window.py  # 插件运行窗口
│   ├── plugins/              # 插件目录
│   │   ├── calculator/       # 计算器插件
│   │   ├── currency_converter/ # 汇率换算插件
│   │   └── simple_ledger/    # 简易记账本插件
│   └── utils/                # 工具模块
│       └── icons.py          # FluentIcon 图标管理
└── exported/                 # 导出的插件包
```

## 数据存储

数据库文件保存在用户数据目录，与应用程序分离：

| 平台 | 路径 |
|------|------|
| macOS | `~/Library/Application Support/Treas/treas.db` |
| Windows | `%LOCALAPPDATA%/Treas/treas.db` |
| Linux | `~/.local/share/Treas/treas.db` |

## 如何开发新插件

> 📘 **[完整插件开发指南 →](PLUGIN_DEV_GUIDE.md)**

只需 **2 个文件** 即可创建插件：`plugin.json`（描述清单）+ `widget.py`（UI 实现）。

### 快速示例

```
plugins/my_tool/
├── plugin.json    # 插件描述清单
└── widget.py      # 插件UI实现（继承 PluginBase）
```

插件支持声明第三方依赖（自动检测 + 一键安装）、导出为 zip 分享给其他用户。

详细规范请参阅 **[PLUGIN_DEV_GUIDE.md](PLUGIN_DEV_GUIDE.md)**，包含：
- plugin.json 完整字段说明
- 插件生命周期（on_activate / on_deactivate）
- 可用图标列表
- 依赖管理机制
- 完整示例代码
- 最佳实践与常见问题

## 技术栈

- **GUI**: PyQt5 + [PyQt-Fluent-Widgets](https://qfluentwidgets.com/)
- **数据库**: SQLite
- **架构**: MVC + 插件系统
- **Python**: 3.9+

## 许可证

MIT License