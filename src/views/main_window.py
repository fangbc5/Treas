"""主窗口 - 基于 QFluentWidgets FluentWindow"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QScrollArea, QFileDialog,
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
    RoundMenu, Action, Dialog, MessageBox,
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
    """工具网格页面 - 展示一组工具卡片

    设计原则：结构固定，内容可变
    - _init_ui() 中一次性创建所有固定结构（header、scroll、grid、empty_label）
    - update_plugins() 只更新网格内的卡片内容，不创建/销毁容器
    """

    def __init__(self, parent=None, show_actions: bool = False, title: str = "全部工具"):
        super().__init__(parent)
        self.tool_cards = []
        self.show_actions = show_actions
        self._plugins = []
        self._page_title = title
        self._title_label = None
        self._scroll = None
        self._grid = None
        self._grid_container = None
        self._empty_label = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 20, 36, 20)
        layout.setSpacing(12)

        # 顶部操作栏
        header_layout = QHBoxLayout()
        self._title_label = SubtitleLabel("全部工具")
        header_layout.addWidget(self._title_label)
        header_layout.addStretch()

        if self.show_actions:
            reset_btn = self._create_header_button("重置内置工具", FluentIcon.SYNC)
            reset_btn.clicked.connect(lambda: self._get_main_window()._reset_builtin_plugins())
            header_layout.addWidget(reset_btn)

            add_btn = self._create_header_button("新建分类", FluentIcon.ADD, primary=True)
            add_btn.clicked.connect(lambda: self._get_main_window()._add_category())
            header_layout.addWidget(add_btn)

            import_btn = self._create_header_button("导入插件", FluentIcon.DOWNLOAD)
            import_btn.clicked.connect(lambda: self._get_main_window()._import_plugin())
            header_layout.addWidget(import_btn)

        layout.addLayout(header_layout)

        # 占位空提示（固定结构，与 scroll 互斥显示）
        self._empty_label = QLabel("暂无工具")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet("color: gray; font-size: 16px; padding: 60px;")
        layout.addWidget(self._empty_label)

        # 滚动区域 + 网格容器（固定结构，初始化一次）
        self._grid_container = QWidget()
        self._grid = QGridLayout(self._grid_container)
        self._grid.setSpacing(16)
        self._grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._scroll.setWidget(self._grid_container)
        layout.addWidget(self._scroll)

        # 初始状态：无工具，显示空提示，隐藏滚动区
        self._empty_label.show()
        self._scroll.hide()

    @staticmethod
    def _create_header_button(text: str, fluent_icon, primary: bool = False):
        """创建工具栏按钮"""
        btn = PrimaryPushButton(text) if primary else PushButton(text)
        btn.setIcon(fluent_icon)
        return btn

    def _get_main_window(self):
        """向上遍历父级链找到 MainWindow"""
        p = self.parent()
        while p is not None:
            if isinstance(p, MainWindow):
                return p
            p = p.parent()
        return None

    def update_plugins(self, plugins: list):
        """刷新页面内容（只更新网格内的卡片，不重建容器）"""
        # 1. 清理旧卡片
        for card in self.tool_cards:
            self._grid.removeWidget(card)
            card.deleteLater()
        self.tool_cards.clear()
        self._plugins = plugins

        # 2. 更新标题
        count = len(plugins)
        self._title_label.setText(f"{self._page_title} ({count})")

        # 3. 切换空提示/滚动区的显示
        if not plugins:
            self._empty_label.show()
            self._scroll.hide()
            return

        self._empty_label.hide()
        self._scroll.show()

        # 4. 创建新卡片并加入网格
        cols = 3
        for i, plugin in enumerate(plugins):
            card = ToolCard(plugin)
            row = i // cols
            col = i % cols
            self._grid.addWidget(card, row, col)
            self.tool_cards.append(card)


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

        # 延迟安装导航项的右键菜单（需要在导航面板完全构建后）
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, self._install_nav_context_menus)

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
            page = ToolGridPage(self, title=cat["name"])
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
                card.open_requested.disconnect()
            except Exception:
                pass
            try:
                card.export_requested.disconnect()
            except Exception:
                pass
            try:
                card.delete_requested.disconnect()
            except Exception:
                pass
            card.open_requested.connect(self._open_plugin)
            card.export_requested.connect(self._export_single_plugin)
            card.delete_requested.connect(self._delete_plugin)
            card.change_category_requested.connect(self._change_plugin_category)

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
                msg = MessageBox(
                    "确认删除",
                    f"确定要删除分类「{cat['name']}」吗？",
                    self,
                )
                if msg.exec():
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
                        page._page_title = data["name"]
                        page._title_label.setText(f"{data['name']} ({len(page._plugins)})")
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

    def _change_plugin_category(self, plugin_id: str):
        """修改插件分类"""
        categories = self.cm.get_all()
        cat_names = [c["name"] for c in categories]
        # 添加"无分类"选项
        items = ["无分类"] + cat_names

        # 获取当前分类
        current_cat = self.pm.get_plugin_category_name(plugin_id)
        current_text = current_cat if current_cat else "无分类"

        item, ok = QInputDialog.getItem(
            self, "修改分类",
            f"选择工具「{plugin_id}」的分类:",
            items,
            items.index(current_text) if current_text in items else 0,
            False,
        )
        if not ok:
            return

        new_cat = None if item == "无分类" else item
        self.pm.set_plugin_category(plugin_id, new_cat)
        self.refresh_all()
        InfoBar.success(
            "已更新",
            f"工具分类已修改为「{item}」",
            parent=self,
            duration=2000,
            position=InfoBarPosition.TOP,
        )

    def _import_plugin(self):
        zip_path, _ = QFileDialog.getOpenFileName(
            self, "选择插件包", "", "Zip 文件 (*.zip)",
            options=QFileDialog.DontUseNativeDialog,
        )
        if not zip_path:
            return
        try:
            plugin_id = self.sm.import_plugin(zip_path)

            # 导入成功后，弹出分类选择
            categories = self.cm.get_all()
            cat_names = [c["name"] for c in categories]
            items = ["不选择（仅在全部工具中显示）"] + cat_names

            item, ok = QInputDialog.getItem(
                self, "选择分类",
                f"插件「{plugin_id}」导入成功，请选择分类:",
                items, 0, False,
            )
            if ok and item != items[0]:
                self.pm.set_plugin_category(plugin_id, item)

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

    def _delete_plugin(self, plugin_id: str):
        """删除插件"""
        meta = self.pm.get_plugin_meta(plugin_id)
        if not meta:
            return

        plugin_name = meta.get("name", plugin_id)
        is_builtin = self.pm.is_builtin(plugin_id)

        # 根据是否内置插件显示不同提示
        if is_builtin:
            hint = f"确定要删除内置工具「{plugin_name}」吗？\n\n内置工具删除后可通过「重置内置工具」按钮恢复。"
        else:
            hint = f"确定要删除工具「{plugin_name}」吗？\n\n此操作将彻底删除该工具，无法恢复！"

        msg = MessageBox("确认删除", hint, self)
        if not msg.exec():
            return

        try:
            self.pm.delete_plugin(plugin_id)
            self.refresh_all()
            InfoBar.success(
                "已删除",
                f"工具「{plugin_name}」已删除",
                parent=self,
                duration=3000,
                position=InfoBarPosition.TOP,
            )
        except Exception as e:
            InfoBar.error(
                "删除失败",
                str(e),
                parent=self,
                duration=3000,
                position=InfoBarPosition.TOP,
            )

    def _reset_builtin_plugins(self):
        """重置所有内置工具（恢复被删除的内置工具）"""
        count = self.pm.reset_builtin_plugins()
        if count > 0:
            self.refresh_all()
            InfoBar.success(
                "重置成功",
                f"已恢复 {count} 个内置工具",
                parent=self,
                duration=3000,
                position=InfoBarPosition.TOP,
            )
        else:
            InfoBar.info(
                "提示",
                "所有内置工具均未隐藏，无需重置",
                parent=self,
                duration=2000,
                position=InfoBarPosition.TOP,
            )

    # ========== 导航栏右键排序 ==========

    def eventFilter(self, obj, event):
        """事件过滤器 - 捕获导航项右键点击"""
        from PyQt5.QtCore import QEvent
        if hasattr(self, '_nav_cat_map') and obj in self._nav_cat_map:
            if event.type() == QEvent.ContextMenu:
                cat_name = self._nav_cat_map[obj]
                global_pos = event.globalPos()
                self._show_nav_context_menu(cat_name, global_pos)
                return True
        return super().eventFilter(obj, event)

    def _show_nav_context_menu(self, cat_name, global_pos):
        """显示导航项右键菜单"""
        categories = self.cm.get_all()
        cat = next((c for c in categories if c["name"] == cat_name), None)
        if not cat:
            return

        clicked_idx = next(
            (i for i, c in enumerate(categories) if c["id"] == cat["id"]),
            None,
        )
        if clicked_idx is None:
            return

        menu = RoundMenu(parent=self)

        # 编辑分类
        edit_action = Action(FluentIcon.EDIT.icon(), "编辑分类")
        edit_action.triggered.connect(lambda: self._edit_category(cat))
        menu.addAction(edit_action)

        menu.addSeparator()

        if clicked_idx > 0:
            up_action = Action(FluentIcon.UP.icon(), "上移")
            up_action.triggered.connect(lambda: self._move_category(cat, "up"))
            menu.addAction(up_action)

        if clicked_idx < len(categories) - 1:
            down_action = Action(FluentIcon.DOWN.icon(), "下移")
            down_action.triggered.connect(lambda: self._move_category(cat, "down"))
            menu.addAction(down_action)

        menu.exec_(global_pos)

    def _install_nav_context_menus(self):
        """为每个分类导航项安装事件过滤器（右键菜单）"""
        panel = self.navigationInterface.panel
        self._nav_cat_map = {}  # nav_widget -> cat_name
        for cat_name, page in self._category_pages.items():
            obj_name = page.objectName()
            if obj_name in panel.items:
                nav_widget = panel.items[obj_name].widget
                self._nav_cat_map[nav_widget] = cat_name
                nav_widget.installEventFilter(self)

    def _move_category(self, cat: dict, direction: str):
        """移动分类顺序（up / down）"""
        categories = self.cm.get_all()
        cat_ids = [c["id"] for c in categories]

        idx = next(
            (i for i, c in enumerate(categories) if c["id"] == cat["id"]),
            None,
        )
        if idx is None:
            return

        if direction == "up" and idx > 0:
            cat_ids[idx], cat_ids[idx - 1] = cat_ids[idx - 1], cat_ids[idx]
        elif direction == "down" and idx < len(cat_ids) - 1:
            cat_ids[idx], cat_ids[idx + 1] = cat_ids[idx + 1], cat_ids[idx]
        else:
            return

        # 更新数据库排序
        self.cm.update_order(cat_ids)

        # 即时重建导航顺序
        self._rebuild_navigation()

        InfoBar.success(
            "排序已更新",
            f"分类「{cat['name']}」已{'上移' if direction == 'up' else '下移'}",
            parent=self,
            duration=2000,
            position=InfoBarPosition.TOP,
        )

    def _rebuild_navigation(self):
        """重建导航栏分类顺序（即时生效）"""
        # 1. 从导航中移除所有分类页面（不删除页面对象）
        old_pages = {}
        for name in list(self._category_pages.keys()):
            page = self._category_pages[name]
            old_pages[name] = page
            # 从导航中移除（只移除导航项，不操作 stackedWidget）
            self.navigationInterface.removeWidget(page.objectName())
        self._category_pages.clear()

        # 2. 按新顺序重新追加到导航末尾
        categories = self.cm.get_all()
        for cat in categories:
            name = cat["name"]
            page = old_pages[name]
            routeKey = page.objectName()
            icon = fluent_icon_from_name(cat.get("icon", "APPLICATION"))

            # addItem 会追加到导航列表末尾
            self.navigationInterface.addItem(
                routeKey=routeKey,
                icon=icon,
                text=name,
                onClick=lambda checked=False, p=page: self.switchTo(p),
                selectable=True,
                tooltip=name,
            )

            self._category_pages[name] = page

        # 3. 重新安装右键菜单
        self._install_nav_context_menus()
