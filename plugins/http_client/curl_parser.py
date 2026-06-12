"""cURL 命令解析器 - 将 cURL 命令转换为 HttpRequest 对象"""

import json
import re
import shlex
from typing import Optional


def parse_curl(curl_cmd: str) -> Optional[dict]:
    """解析 cURL 命令，返回请求数据字典

    支持的 cURL 选项：
        -X, --request     请求方法
        -H, --header      请求头
        -d, --data         请求体
        --data-raw         原始请求体
        --data-urlencode   URL 编码请求体
        -F, --form         表单数据
        -u, --user         Basic 认证
        -b, --cookie       Cookie
        -k, --insecure     忽略 SSL
        -L, --location     跟随重定向
        --url              URL

    Returns:
        {
            "method": "GET",
            "url": "https://...",
            "headers": [{"key": "", "value": "", "enabled": True}],
            "params": [{"key": "", "value": "", "enabled": True}],
            "body_type": "none",
            "body_content": "",
            "auth_type": "none",
            "auth_config": {}
        }
    """
    if not curl_cmd or not curl_cmd.strip():
        return None

    # 清理输入
    cmd = curl_cmd.strip()
    # 移除行尾续行符
    cmd = cmd.replace("\\\n", " ").replace("\\\r\n", " ")

    # 尝试使用 shlex 解析，失败则用正则
    try:
        tokens = shlex.split(cmd)
    except ValueError:
        tokens = _simple_tokenize(cmd)

    if not tokens:
        return None

    # 移除开头的 curl 命令
    if tokens[0].lower() == "curl":
        tokens = tokens[1:]

    result = {
        "method": "",
        "url": "",
        "headers": [],
        "params": [],
        "body_type": "none",
        "body_content": "",
        "auth_type": "none",
        "auth_config": {},
    }

    has_data = False
    is_form = False

    i = 0
    while i < len(tokens):
        token = tokens[i]

        # 请求方法
        if token in ("-X", "--request"):
            i += 1
            if i < len(tokens):
                result["method"] = tokens[i].upper()

        # 请求头
        elif token in ("-H", "--header"):
            i += 1
            if i < len(tokens):
                header = _parse_header(tokens[i])
                if header:
                    result["headers"].append(header)

        # Cookie
        elif token in ("-b", "--cookie"):
            i += 1
            if i < len(tokens):
                result["headers"].append({
                    "key": "Cookie",
                    "value": tokens[i],
                    "enabled": True,
                })

        # 请求体（JSON/text）
        elif token in ("-d", "--data", "--data-raw", "--data-binary", "--data-urlencode"):
            i += 1
            if i < len(tokens):
                has_data = True
                data = tokens[i]
                # 如果是 @file 格式，跳过
                if not data.startswith("@"):
                    result["body_content"] = data
                    # 检测 JSON
                    if data.strip().startswith("{") or data.strip().startswith("["):
                        result["body_type"] = "json"
                    else:
                        result["body_type"] = "raw"
                    # 自动设置 Content-Type
                    if not any(h["key"].lower() == "content-type" for h in result["headers"]):
                        result["headers"].append({
                            "key": "Content-Type",
                            "value": "application/x-www-form-urlencoded",
                            "enabled": True,
                        })

        # 表单数据
        elif token in ("-F", "--form"):
            i += 1
            if i < len(tokens):
                has_data = True
                is_form = True
                result["body_type"] = "form_data"
                # 简化处理：将 form 字段存为 JSON 数组
                form_items = []
                try:
                    form_items = json.loads(result["body_content"])
                except Exception:
                    form_items = []
                if "=" in tokens[i]:
                    k, v = tokens[i].split("=", 1)
                    form_items.append({"key": k, "value": v, "enabled": True})
                result["body_content"] = json.dumps(form_items, ensure_ascii=False)

        # Basic 认证
        elif token in ("-u", "--user"):
            i += 1
            if i < len(tokens):
                result["auth_type"] = "basic"
                parts = tokens[i].split(":", 1)
                result["auth_config"] = {
                    "username": parts[0] if len(parts) > 0 else "",
                    "password": parts[1] if len(parts) > 1 else "",
                }

        # Authorization header（bearer token）
        elif token == "-H" and i + 1 < len(tokens) and tokens[i + 1].lower().startswith("authorization:"):
            pass  # 已在 header 处理中处理

        # 忽略的选项
        elif token in ("-k", "--insecure", "-L", "--location", "-s", "--silent",
                        "-S", "--show-error", "-v", "--verbose", "-i", "--include",
                        "-I", "--head", "--compressed"):
            if token in ("-I", "--head"):
                result["method"] = "HEAD"

        # 输出文件（忽略）
        elif token in ("-o", "--output"):
            i += 1  # 跳过文件名

        # --url
        elif token == "--url":
            i += 1
            if i < len(tokens):
                result["url"] = tokens[i]

        # URL（不以 - 开头的参数）
        elif not token.startswith("-") and not result["url"]:
            result["url"] = token

        i += 1

    # 自动推断方法
    if not result["method"]:
        if has_data:
            result["method"] = "POST"
        else:
            result["method"] = "GET"

    # 如果 body_type 是 json 且有 Content-Type 为 form，修正
    if is_form:
        result["body_type"] = "form_data"

    # 如果没有 URL，返回 None
    if not result["url"]:
        return None

    # 解析 URL 中的查询参数
    url = result["url"]
    if "?" in url:
        base_url, query_string = url.split("?", 1)
        result["url"] = base_url
        for param in query_string.split("&"):
            if "=" in param:
                k, v = param.split("=", 1)
                result["params"].append({"key": k, "value": v, "enabled": True})
            else:
                result["params"].append({"key": param, "value": "", "enabled": True})

    return result


def _parse_header(header_str: str) -> Optional[dict]:
    """解析单个请求头字符串"""
    if ":" not in header_str:
        return None

    key, value = header_str.split(":", 1)
    return {
        "key": key.strip(),
        "value": value.strip(),
        "enabled": True,
    }


def _simple_tokenize(cmd: str) -> list:
    """简单的命令行分词（shlex 解析失败时使用）"""
    tokens = []
    current = ""
    in_single_quote = False
    in_double_quote = False

    for char in cmd:
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
        elif char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
        elif char in (' ', '\t') and not in_single_quote and not in_double_quote:
            if current:
                tokens.append(current)
                current = ""
        else:
            current += char

    if current:
        tokens.append(current)

    return tokens

