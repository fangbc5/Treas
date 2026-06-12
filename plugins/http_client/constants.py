"""HTTP 客户端 - 常量与样式表"""

# ========== 请求方法 ==========
HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]

METHOD_COLORS = {
    "GET": "#27ae60",
    "POST": "#f39c12",
    "PUT": "#3498db",
    "DELETE": "#e74c3c",
    "PATCH": "#9b59b6",
    "HEAD": "#95a5a6",
    "OPTIONS": "#95a5a6",
}

# ========== Body 类型 ==========
BODY_TYPES = ["none", "json", "form_data", "urlencoded", "raw"]

BODY_TYPE_LABELS = {
    "none": "无",
    "json": "JSON",
    "form_data": "Form Data",
    "urlencoded": "x-www-form-urlencoded",
    "raw": "Raw Text",
}

# ========== 认证类型 ==========
AUTH_TYPES = ["none", "basic", "bearer", "api_key"]

AUTH_TYPE_LABELS = {
    "none": "无认证",
    "basic": "Basic Auth",
    "bearer": "Bearer Token",
    "api_key": "API Key",
}

# ========== 样式表 ==========
GLOBAL_STYLE = """
QWidget {
    font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
}
"""

REQUEST_BAR_STYLE = """
QWidget#requestBar {
    background-color: white;
    border-bottom: 1px solid #e0e0e0;
}
"""

RESPONSE_BODY_STYLE = """
QTextEdit {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: none;
    border-radius: 6px;
    padding: 12px;
    font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
    font-size: 13px;
    selection-background-color: #45475a;
    selection-color: #cdd6f4;
}
"""