"""图标工具模块 - 基于 QFluentWidgets FluentIcon"""

from qfluentwidgets import FluentIcon, Icon, getIconColor, themeColor
from PyQt5.QtGui import QIcon


# ===== 分类可选图标 =====
# (FluentIcon 枚举, 显示名)
CATEGORY_ICONS = [
    (FluentIcon.FOLDER, "文件夹"),
    (FluentIcon.APPLICATION, "应用"),
    (FluentIcon.SYNC, "同步"),
    (FluentIcon.LIBRARY, "库"),
    (FluentIcon.LAYOUT, "布局"),
    (FluentIcon.SHOPPING_CART, "购物"),
    (FluentIcon.HEART, "收藏"),
    (FluentIcon.PIN, "置顶"),
    (FluentIcon.TAG, "标签"),
    (FluentIcon.PEOPLE, "用户"),
    (FluentIcon.MAIL, "邮件"),
    (FluentIcon.GAME, "游戏"),
    (FluentIcon.PHOTO, "照片"),
    (FluentIcon.MUSIC, "音乐"),
    (FluentIcon.VIDEO, "视频"),
    (FluentIcon.GLOBE, "全球"),
]

# 默认分类图标
CATEGORY_DEFAULTS = {
    "计算工具": FluentIcon.APPLICATION,
    "转换工具": FluentIcon.SYNC,
    "记账工具": FluentIcon.LIBRARY,
}

# UI 图标映射
UI_ICONS = {
    "all_tools": FluentIcon.HOME,
    "add": FluentIcon.ADD,
    "manage": FluentIcon.SETTING,
    "import": FluentIcon.DOWNLOAD,
    "export": FluentIcon.IMAGE_EXPORT,
    "refresh": FluentIcon.UPDATE,
    "delete": FluentIcon.DELETE,
    "open": FluentIcon.PLAY,
    "share": FluentIcon.SHARE,
    "search": FluentIcon.SEARCH,
    "close": FluentIcon.CLOSE,
    "edit": FluentIcon.EDIT,
    "save": FluentIcon.SAVE,
    "menu": FluentIcon.MENU,
}


def get_fluent_icon(icon_key: str) -> FluentIcon:
    """根据 key 获取 FluentIcon 枚举"""
    if icon_key in UI_ICONS:
        return UI_ICONS[icon_key]
    return FluentIcon.APPLICATION


def fluent_icon_from_name(name: str) -> FluentIcon:
    """从图标名称字符串获取 FluentIcon
    
    支持:
      - FluentIcon 枚举名 如 "APPLICATION"
      - UI key 如 "add", "delete"
    """
    # 先查 UI_ICONS
    if name in UI_ICONS:
        return UI_ICONS[name]

    # 再查 FluentIcon 枚举
    if hasattr(FluentIcon, name.upper()):
        return getattr(FluentIcon, name.upper())

    # 默认
    return FluentIcon.APPLICATION


def icon_to_string(icon) -> str:
    """将图标转为可存储的字符串"""
    if isinstance(icon, FluentIcon):
        return icon.name
    if isinstance(icon, str):
        return icon
    return "APPLICATION"