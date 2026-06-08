"""分类管理器 - 分类的 CRUD 操作"""

from src.core.database import Database


class CategoryManager:
    """分类管理器"""

    def __init__(self):
        self.db = Database()

    def get_all(self) -> list:
        """获取所有分类"""
        return self.db.query(
            "SELECT * FROM categories ORDER BY sort_order ASC, id ASC"
        )

    def get_by_id(self, category_id: int) -> dict:
        """根据ID获取分类"""
        return self.db.query_one(
            "SELECT * FROM categories WHERE id = ?", (category_id,)
        )

    def get_by_name(self, name: str) -> dict:
        """根据名称获取分类"""
        return self.db.query_one(
            "SELECT * FROM categories WHERE name = ?", (name,)
        )

    def create(self, name: str, icon: str = "FOLDER", sort_order: int = 0) -> int:
        """创建分类"""
        cursor = self.db.execute(
            "INSERT INTO categories (name, icon, sort_order) VALUES (?, ?, ?)",
            (name, icon, sort_order),
        )
        return cursor.lastrowid

    def update(self, category_id: int, name: str = None, icon: str = None,
               sort_order: int = None) -> bool:
        """更新分类"""
        updates = []
        params = []
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if icon is not None:
            updates.append("icon = ?")
            params.append(icon)
        if sort_order is not None:
            updates.append("sort_order = ?")
            params.append(sort_order)

        if not updates:
            return False

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(category_id)

        self.db.execute(
            f"UPDATE categories SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        return True

    def delete(self, category_id: int) -> bool:
        """删除分类"""
        self.db.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        return True

    def update_order(self, ordered_ids: list):
        """批量更新分类排序顺序"""
        for index, cat_id in enumerate(ordered_ids):
            self.db.execute(
                "UPDATE categories SET sort_order = ? WHERE id = ?",
                (index + 1, cat_id),
            )

    def get_category_names(self) -> list:
        """获取所有分类名称列表"""
        rows = self.get_all()
        return [row["name"] for row in rows]

    def ensure_default_categories(self):
        """确保默认分类存在"""
        defaults = [
            ("计算工具", "APPLICATION", 1),
            ("转换工具", "SYNC", 2),
            ("记账工具", "LIBRARY", 3),
        ]
        for name, icon, order in defaults:
            existing = self.get_by_name(name)
            if not existing:
                self.create(name, icon, order)