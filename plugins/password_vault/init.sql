-- 密码保险箱数据库初始化

-- 主密码哈希（仅存一行）
CREATE TABLE IF NOT EXISTS master_key (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 密码条目
CREATE TABLE IF NOT EXISTS vault_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL DEFAULT 'login',
    title TEXT NOT NULL,
    username TEXT DEFAULT '',
    password_encrypted TEXT DEFAULT '',
    url TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    custom_fields TEXT DEFAULT '{}',
    is_favorite INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_vault_category ON vault_entries(category);
CREATE INDEX IF NOT EXISTS idx_vault_favorite ON vault_entries(is_favorite);
CREATE INDEX IF NOT EXISTS idx_vault_title ON vault_entries(title);