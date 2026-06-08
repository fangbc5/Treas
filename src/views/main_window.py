"""主窗口 - 基于 QFluentWidgets FluentWindow"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QScrollArea, QFileDialog, QMessageBox,
    QInputDialog, QSizePolicy,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QDialog
from PyQt5.QtGui import QFont

from qfluentwidgets import (
    FluentWindow, FluentIcon, NavigationItemPosition,
    SubtitleLabel, CaptionLabel, PushButton, PrimaryPushButton,
    TransparentToolButton, ToolButton, InfoBar, InfoBarPosition,
    CardWidget, HeaderCardWidget, StrongBodyLabel,
    RoundMenu, Action, Dialog,
    setFont,
)

from src.core.plugin_manager import PluginManager
from src.core.category_manager import CategoryManager
from src.core.share_manager import ShareManager
from src.utils.icons import (
    CATEGORY_ICONS, UI_ICONS, get_fluent_icon, fluent_icon_from_name,
)
from src.views.tool_card import ToolCard
from src.views.category_dialog import CategoryDialog


class ToolGridPage(QWidget):
    """工具网格页面 - 展示一组工具卡片"""

    def __init__(self, parent=None, show_actions: bool = False):
        super().__init__(parent)
        self.tool_cards = []
        self.show_actions = show_actions
        self._plugins = []
        self._layout = None
        self._header_layout = None
        self._grid_container = None
        self._grid = None
        self._scroll = None
        self._title_label = None
        self._init_ui()

    def _init_ui(self):
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(36, 20, 36, 20)
        self._layout.setSpacing(12)

        # 顶部操作栏
        self._header_layout = QHBoxLayout()
        self._title_label = SubtitleLabel("全部工具")
        self._header_layout.addWidget(self._title_label)
        self._header_layout.addStretch()

        if self.show_actions:
            add_btn = PrimaryPushButton(" 新建分类")
            add_btn.setIcon(FluentIcon.ADD.icon())
            add_btn.clicked.connect(lambda: self._get_main_window()._add_category())
            self._header_layout.addWidget(add_btn)

            manage_btn = PushButton(" 管理分类")
            manage_btn.setIcon(FluentIcon.SETTING.icon())
            manage_btn.clicked.connect(
                lambda: self._get_main_window()._manage_category_from_toolbar()
            )
            self._header_layout.addWidget(manage_btn)

        self._layout.addLayout(self._header_layout)

        # 占位空提示
        self._empty_label = QLabel("暂无工具")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet("color: gray; font-size: 16px; padding: 60px;")
        self._layout.addWidget(self._empty_label)

    def _get_main_window(self):
        p = self.parent()
        return p

    def update_plugins(self, plugins: list):
        """刷新页面内容"""
        # 清理旧的卡片和网格
        if self._grid_container is not None:
            self._scroll.setWidget(None)
            self._grid_container.deleteLater()
            self._grid_container = None
            self._scroll = None

        self.tool_cards.clear()
        self._plugins = plugins

        # 更新标题
        count = len(plugins)
        self._title_label.setText(f"全部工具 ({count})" if self.show_actions else f"工具 ({count})")

        if not plugins:
            self._empty_label.show()
            return

        self._empty_label.hide()

        # 创建新的网格
        self._grid_container = QWidget()
        self._grid = QGridLayout(self._grid_container)
        self._grid.setSpacing(16)
        self._grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        cols = 3
        for i, plugin in enumerate(plugins):
            card = ToolCard(plugin)
            row = i // cols
            col = i % cols
            self._grid.addWidget(card, row, col)
            self.tool_cards.append(card)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._scroll.setWidget(self._grid_container)
        self._layout.addWidget(self._scroll)


class MainWindow(FluentWindow):
    """应用程序主窗口 - Fluent 风格"""

    def __init__(self):
        super().__init__()
        self.pm = PluginManager()
        self.cm = CategoryManager()
        self.sm = ShareManager()

        self._category_pages = {}  # category_name -> ToolGridPage
        self._all_page = None

        self._init_window()
        self._init_navigation()

    def _init_window(self):
        self.setWindowTitle("Treas - 财务工具箱")
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)
        self.setWindowIcon(FluentIcon.APPLICATION.icon())

        # 缩小导航栏展开宽度 (默认约 300，太宽)
        self.navigationInterface.setExpandWidth(200)

    def _init_navigation(self):
        """初始化导航栏"""
        # 「全部工具」页
        self._all_page = ToolGridPage(self, show_actions=True)
        self._all_page.setObjectName("allPage")
        self.addSubInterface(self._all_page, FluentIcon.HOME, "全部工具")

        # 加载分类页面
        self._load_category_pages()

        # 刷新全部工具页内容
        self._refresh_all_page()

    def _load_category_pages(self):
        """加载分类页面到导航"""
        categories = self.cm.get_all()

        for cat in categories:
            plugins = self.pm.get_plugins_by_category(cat["name"])
            page = ToolGridPage(self)
            page.setObjectName(f"catPage_{cat['id']}")
            page.update_plugins(plugins)
            icon = fluent_icon_from_name(cat.get("icon", "APPLICATION"))

            self.addSubInterface(page, icon, cat["name"])
            self._category_pages[cat["name"]] = page

            # 连接卡片信号
            self._connect_card_signals(page)

    def _connect_card_signals(self, page: ToolGridPage):
        """连接页面中卡片的信号"""
        for card in page.tool_cards:
            try:
                card.clicked.disconnect()
            except Exception:
                pass
            try:
                card.export_requested.disconnect()
            except Exception:
                pass
            card.clicked.connect(self._open_plugin)
            card.export_requested.connect(self._export_single_plugin)

    def _refresh_all_page(self):
        """刷新全部工具页"""
        all_plugins = self.pm.list_plugins()
        self._all_page.update_plugins(all_plugins)
        self._connect_card_signals(self._all_page)

    def _refresh_category_pages(self):
        """刷新分类页内容"""
        for name, page in self._category_pages.items():
            plugins = self.pm.get_plugins_by_category(name)
            page.update_plugins(plugins)
            self._connect_card_signals(page)

    def refresh_all(self):
        """刷新所有页面内容（不重建导航）"""
        self._refresh_category_pages()
        self._refresh_all_page()

    def _add_category(self):
        dialog = CategoryDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                max_order = len(self.cm.get_all())
                icon_name = data.get("icon", "APPLICATION")
                cat_id = self.cm.create(data["name"], icon_name, max_order + 1)

                # 添加新页面到导航
                page = ToolGridPage(self)
                page.setObjectName(f"catPage_{cat_id}")
                icon = fluent_icon_from_name(icon_name)
                self.addSubInterface(page, icon, data["name"])
                self._category_pages[data["name"]] = page

                self._refresh_all_page()

                InfoBar.success(
                    "成功",
                    f"分类「{data['name']}」已创建",
                    parent=self,
                    duration=3000,
                    position=InfoBarPosition.TOP,
                )
            except Exception as e:
                InfoBar.error(
                    "错误",
                    f"创建分类失败: {e}",
                    parent=self,
                    duration=3000,
                    position=InfoBarPosition.TOP,
                )

    def _manage_category_from_toolbar(self):
        """管理分类 - 从工具栏触发"""
        categories = self.cm.get_all()
        if not categories:
            InfoBar.warning("提示", "暂无分类可管理", parent=self, duration=2000)
            return

        menu = RoundMenu(parent=self)
        for cat in categories:
            action = Action(FluentIcon.EDIT.icon(), cat["name"])
            action.triggered.connect(
                lambda checked, c=cat: self._edit_category(c)
            )
            menu.addAction(action)

        menu.addSeparator()

        import_action = Action(FluentIcon.DOWNLOAD.icon(), "导入插件包")
        import_action.triggered.connect(self._import_plugin)
        menu.addAction(import_action)

        menu.exec_(self.mapToGlobal(self.rect().center()))

    def _edit_category(self, cat: dict):
        """编辑分类"""
        dialog = CategoryDialog(self, cat)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            action = data.get("action")
            if action == "delete":
                reply = QMessageBox.question(
                    self, "确认删除",
                    f"确定要删除分类「{cat['name']}」吗？",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply == QMessageBox.Yes:
                    self.cm.delete(cat["id"])
                    # 标记页面待删除（实际无法从导航移除，只清空内容）
                    if cat["name"] in self._category_pages:
                        page = self._category_pages[cat["name"]]
                        page.update_plugins([])
                        page._title_label.setText(f"{cat['name']} (已删除)")
                    del self._category_pages[cat["name"]]
                    self._refresh_all_page()
                    InfoBar.success(
                        "已删除",
                        f"分类「{cat['name']}」已删除（重启后生效）",
                        parent=self,
                        duration=3000,
                    )
            else:
                try:
                    self.cm.update(cat["id"], name=data["name"], icon=data.get("icon"))
                    # 更新页面标题
                    if cat["name"] in self._category_pages:
                        page = self._category_pages[cat["name"]]
                        page._title_label.setText(data["name"])
                        # 更新映射
                        self._category_pages[data["name"]] = page
                        if data["name"] != cat["name"]:
                            del self._category_pages[cat["name"]]
                    self._refresh_all_page()
                    InfoBar.success(
                        "已更新",
                        "分类信息已更新",
                        parent=self,
                        duration=3000,
                    )
                except Exception as e:
                    InfoBar.error("错误", f"更新失败: {e}", parent=self, duration=3000)

    def _open_plugin(self, plugin_id: str):
        plugin = self.pm.get_plugin(plugin_id)
        if plugin is None:
            InfoBar.error("错误", f"无法加载插件: {plugin_id}", parent=self, duration=3000)
            return
        from src.views.plugin_window import PluginWindow
        win = PluginWindow(plugin, self)
        win.show()

    def _import_plugin(self):
        zip_path, _ = QFileDialog.getOpenFileName(
            self, "选择插件包", "", "Zip 文件 (*.zip)"
        )
        if not zip_path:
            return
        try:
            plugin_id = self.sm.import_plugin(zip_path)
            self.refresh_all()
            InfoBar.success(
                "导入成功",
                f"插件 {plugin_id} 已成功导入",
                parent=self,
                duration=3000,
            )
        except Exception as e:
            InfoBar.error("导入失败", str(e), parent=self, duration=5000)

    def _export_plugin(self):
        plugins = self.pm.list_plugins()
        if not plugins:
            InfoBar.info("提示", "暂无可导出的插件", parent=self, duration=2000)
            return
        names = [f"{p['name']} ({p['id']})" for p in plugins]
        name, ok = QInputDialog.getItem(
            self, "导出插件", "选择要导出的插件:", names, 0, False
        )
        if not ok:
            return
        plugin_id = name.split("(")[-1].rstrip(")")
        self._export_single_plugin(plugin_id)

    def _export_single_plugin(self, plugin_id: str):
        try:
            zip_path = self.sm.export_plugin(plugin_id)
            InfoBar.success(
                "导出成功",
                f"已导出到: {zip_path}",
                parent=self,
                duration=5000,
            )
        except Exception as e:
            InfoBar.error("导出失败", str(e), parent=self, duration=5000)