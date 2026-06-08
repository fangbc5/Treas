"""插件基类 - 所有工具插件必须继承此类"""

from PyQt5.QtWidgets import QWidget


class PluginBase(QWidget):
    """插件基类，定义统一接口"""

    # 子类必须覆盖以下属性
    plugin_id = ""
    plugin_name = ""
    plugin_version = "1.0.0"
    plugin_description = ""
    plugin_icon = "🔧"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active = False

    def get_widget(self) -> QWidget:
        """返回插件的UI组件"""
        return self

    def on_activate(self):
        """插件被激活时调用"""
        self._active = True

    def on_deactivate(self):
        """插件被关闭/隐藏时调用"""
        self._active = False

    @property
    def is_active(self) -> bool:
        return self._active

    def get_meta(self) -> dict:
        """获取插件元信息"""
        return {
            "id": self.plugin_id,
            "name": self.plugin_name,
            "version": self.plugin_version,
            "description": self.plugin_description,
            "icon": self.plugin_icon,
        }