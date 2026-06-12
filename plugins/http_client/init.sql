-- HTTP 客户端数据库初始化

-- 集合（文件夹概念，支持嵌套）
CREATE TABLE IF NOT EXISTS collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    parent_id INTEGER DEFAULT NULL,
    description TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sort_order INTEGER DEFAULT 0,
    FOREIGN KEY (parent_id) REFERENCES collections(id) ON DELETE CASCADE
);

-- 保存的请求
CREATE TABLE IF NOT EXISTS saved_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id INTEGER,
    name TEXT NOT NULL,
    method TEXT DEFAULT 'GET',
    url TEXT DEFAULT '',
    headers TEXT DEFAULT '{}',
    params TEXT DEFAULT '{}',
    body_type TEXT DEFAULT 'none',
    body_content TEXT DEFAULT '',
    auth_type TEXT DEFAULT 'none',
    auth_config TEXT DEFAULT '{}',
    description TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sort_order INTEGER DEFAULT 0,
    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE SET NULL
);

-- 请求历史（自动记录）
CREATE TABLE IF NOT EXISTS request_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    method TEXT NOT NULL,
    url TEXT NOT NULL,
    headers TEXT DEFAULT '{}',
    params TEXT DEFAULT '{}',
    body_type TEXT DEFAULT 'none',
    body_content TEXT DEFAULT '',
    auth_type TEXT DEFAULT 'none',
    auth_config TEXT DEFAULT '{}',
    status_code INTEGER,
    response_time INTEGER,
    response_size INTEGER,
    response_headers TEXT DEFAULT '{}',
    response_body TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 环境变量组
CREATE TABLE IF NOT EXISTS environments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    variables TEXT DEFAULT '{}',
    is_active INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_saved_requests_collection ON saved_requests(collection_id);
CREATE INDEX IF NOT EXISTS idx_request_history_time ON request_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_environments_active ON environments(is_active);
CREATE INDEX IF NOT EXISTS idx_collections_parent ON collections(parent_id);