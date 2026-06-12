"""HTTP 客户端 - 导入/导出模块

支持 Postman Collection v2.1 格式，兼容 Postman / ApiPost 等工具。
"""

import json
import os
from datetime import datetime


# ========== Postman Collection v2.1 导出 ==========

def export_to_postman_collection(collections, requests, environments=None):
    """将集合和请求导出为 Postman Collection v2.1 格式。

    Parameters
    ----------
    collections : list[dict]
        集合列表，每个含 id, name, parent_id, description
    requests : list[dict]
        请求列表，每个含 id, collection_id, name, method, url,
        headers, params, body_type, body_content, auth_type, auth_config
    environments : list[dict] | None
        环境变量列表，每个含 name, variables

    Returns
    -------
    dict
        Postman Collection v2.1 格式的字典
    """
    # 构建集合树
    children_map = {}  # parent_id -> [coll, ...]
    root_collections = []
    for coll in collections:
        parent_id = coll.get("parent_id")
        if parent_id:
            children_map.setdefault(parent_id, []).append(coll)
        else:
            root_collections.append(coll)

    def build_item(coll):
        """递归构建 Postman item（文件夹 + 请求）"""
        item = {
            "name": coll.get("name", "未命名集合"),
            "description": coll.get("description", ""),
        }

        # 子项（子集合 + 请求）
        sub_items = []

        # 子集合
        for child in children_map.get(coll["id"], []):
            sub_items.append(build_item(child))

        # 该集合下的请求
        for req in requests:
            if req.get("collection_id") == coll["id"]:
                sub_items.append(build_request_item(req))

        if sub_items:
            item["item"] = sub_items

        return item

    def build_request_item(req):
        """构建单个请求的 Postman item"""
        method = req.get("method", "GET")
        url = req.get("url", "")

        # 解析 headers
        headers = _parse_kv_data(req.get("headers", []))
        pm_headers = []
        for h in headers:
            pm_headers.append({
                "key": h["key"],
                "value": h.get("value", ""),
                "disabled": not h.get("enabled", True),
            })

        # 解析 params
        params = _parse_kv_data(req.get("params", []))
        pm_query = []
        for p in params:
            pm_query.append({
                "key": p["key"],
                "value": p.get("value", ""),
                "disabled": not p.get("enabled", True),
            })

        # URL 结构
        url_obj = {
            "raw": url,
            "host": _extract_host(url),
            "path": _extract_path(url),
        }
        if pm_query:
            url_obj["query"] = pm_query

        # Body
        body_obj = None
        body_type = req.get("body_type", "none")
        body_content = req.get("body_content", "")
        if body_type == "json":
            body_obj = {
                "mode": "raw",
                "raw": body_content,
                "options": {"raw": {"language": "json"}},
            }
        elif body_type == "raw":
            body_obj = {
                "mode": "raw",
                "raw": body_content,
            }
        elif body_type == "urlencoded":
            body_obj = {
                "mode": "urlencoded",
                "urlencoded": _parse_body_urlencoded(body_content),
            }
        elif body_type == "form_data":
            body_obj = {
                "mode": "formdata",
                "formdata": _parse_body_formdata(body_content),
            }

        # Auth
        auth_obj = _build_auth(req.get("auth_type", "none"),
                                req.get("auth_config", {}))

        request = {
            "method": method,
            "header": pm_headers if pm_headers else [],
            "url": url_obj,
            "description": req.get("description", ""),
        }
        if body_obj:
            request["body"] = body_obj
        if auth_obj:
            request["auth"] = auth_obj

        return {
            "name": req.get("name", "未命名请求"),
            "request": request,
        }

    # 构建顶层 items
    items = []
    for coll in root_collections:
        items.append(build_item(coll))

    # 如果没有集合但有请求，直接放到顶层
    if not collections:
        for req in requests:
            items.append(build_request_item(req))

    collection = {
        "info": {
            "_postman_id": "treas-export",
            "name": "Treas 导出集合",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            "description": f"由 Treas HTTP 客户端导出，时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        },
        "item": items,
    }

    # 环境变量（作为顶级变量列表）
    if environments:
        variables = []
        for env in environments:
            env_vars = env.get("variables", {})
            if isinstance(env_vars, str):
                try:
                    env_vars = json.loads(env_vars)
                except (json.JSONDecodeError, TypeError):
                    env_vars = {}
            for k, v in env_vars.items():
                variables.append({
                    "key": k,
                    "value": v,
                    "description": f"环境: {env.get('name', '')}",
                })
        if variables:
            collection["variable"] = variables

    return collection


def export_single_request_to_postman(req):
    """导出单个请求为 Postman Collection v2.1 格式。"""
    return export_to_postman_collection([], [req])


# ========== Postman Collection v2.1 导入 ==========

def import_from_postman_collection(data):
    """解析 Postman Collection v2.1 格式，返回集合和请求列表。

    Parameters
    ----------
    data : dict | str
        Postman Collection v2.1 格式的字典或 JSON 字符串

    Returns
    -------
    dict
        {
            "collections": [{"name": ..., "parent_id": ..., "description": ...}],
            "requests": [{"collection_name": ..., "name": ..., "method": ..., ...}],
            "environments": [{"name": ..., "variables": ...}],
        }
    """
    if isinstance(data, str):
        data = json.loads(data)

    result = {
        "collections": [],
        "requests": [],
        "environments": [],
    }

    # 顶层变量（当作环境变量）
    variables = data.get("variable", [])
    if variables:
        env_vars = {}
        for v in variables:
            key = v.get("key", "")
            value = v.get("value", "")
            if key:
                env_vars[key] = value
        if env_vars:
            result["environments"].append({
                "name": "导入环境",
                "variables": env_vars,
            })

    # 解析 items
    items = data.get("item", [])
    for item in items:
        _parse_postman_item(item, parent_name=None, result=result)

    return result


def _parse_postman_item(item, parent_name, result):
    """递归解析 Postman item（可能是文件夹或请求）。"""
    sub_items = item.get("item", None)

    if sub_items is not None:
        # 这是一个文件夹/集合
        coll_name = item.get("name", "未命名集合")
        coll_desc = item.get("description", "")
        result["collections"].append({
            "name": coll_name,
            "parent_name": parent_name,
            "description": coll_desc if isinstance(coll_desc, str) else coll_desc.get("content", "") if isinstance(coll_desc, dict) else "",
        })

        for sub in sub_items:
            _parse_postman_item(sub, parent_name=coll_name, result=result)
    else:
        # 这是一个请求
        req_data = item.get("request", {})

        # 兼容：request 可能是字符串（URL）
        if isinstance(req_data, str):
            req_data = {"url": req_data, "method": "GET"}

        method = req_data.get("method", "GET")

        # URL
        url_obj = req_data.get("url", "")
        if isinstance(url_obj, str):
            url_raw = url_obj
        elif isinstance(url_obj, dict):
            url_raw = url_obj.get("raw", "")
        else:
            url_raw = ""

        # Headers
        headers = []
        for h in req_data.get("header", []):
            headers.append({
                "key": h.get("key", ""),
                "value": h.get("value", ""),
                "enabled": not h.get("disabled", False),
            })

        # Query params
        params = []
        url_dict = req_data.get("url", {}) if isinstance(req_data.get("url"), dict) else {}
        for q in url_dict.get("query", []):
            params.append({
                "key": q.get("key", ""),
                "value": q.get("value", ""),
                "enabled": not q.get("disabled", False),
            })

        # Body
        body_type = "none"
        body_content = ""
        body_obj = req_data.get("body", None)
        if body_obj:
            mode = body_obj.get("mode", "")
            if mode == "raw":
                body_type = "json"  # 默认当 json
                body_content = body_obj.get("raw", "")
                # 检测是否真的是 JSON
                lang = body_obj.get("options", {}).get("raw", {}).get("language", "")
                if lang and lang != "json":
                    body_type = "raw"
                elif body_content.strip():
                    try:
                        json.loads(body_content)
                    except (json.JSONDecodeError, TypeError):
                        body_type = "raw"
            elif mode == "urlencoded":
                body_type = "urlencoded"
                encoded = body_obj.get("urlencoded", [])
                pairs = []
                for e in encoded:
                    pairs.append(f"{e.get('key', '')}={e.get('value', '')}")
                body_content = "&".join(pairs)
            elif mode == "formdata":
                body_type = "form_data"
                form_items = body_obj.get("formdata", [])
                body_content = json.dumps([
                    {"key": f.get("key", ""), "value": f.get("value", ""),
                     "type": f.get("type", "text"), "enabled": not f.get("disabled", False)}
                    for f in form_items
                ], ensure_ascii=False)

        # Auth
        auth_type = "none"
        auth_config = {"type": "none"}
        auth_obj = req_data.get("auth", None) or item.get("auth", None)
        if auth_obj:
            auth_type = auth_obj.get("type", "none")
            if auth_type == "basic":
                basic = auth_obj.get("basic", [])
                username = ""
                password = ""
                for b in basic:
                    if b.get("key") == "username":
                        username = b.get("value", "")
                    elif b.get("key") == "password":
                        password = b.get("value", "")
                auth_config = {"type": "basic", "username": username, "password": password}
            elif auth_type == "bearer":
                bearer = auth_obj.get("bearer", [])
                token = ""
                for b in bearer:
                    if b.get("key") == "token":
                        token = b.get("value", "")
                auth_config = {"type": "bearer", "token": token}
            elif auth_type == "apikey":
                apikey = auth_obj.get("apikey", [])
                key_name = ""
                key_value = ""
                add_to = "header"
                for a in apikey:
                    if a.get("key") == "key":
                        key_name = a.get("value", "")
                    elif a.get("key") == "value":
                        key_value = a.get("value", "")
                    elif a.get("key") == "in":
                        add_to = a.get("value", "header")
                auth_config = {
                    "type": "api_key",
                    "key_name": key_name,
                    "key_value": key_value,
                    "add_to": add_to,
                }
            else:
                auth_type = "none"
                auth_config = {"type": "none"}

        result["requests"].append({
            "collection_name": parent_name,
            "name": item.get("name", "未命名请求"),
            "method": method,
            "url": url_raw,
            "headers": headers,
            "params": params,
            "body_type": body_type,
            "body_content": body_content,
            "auth_type": auth_type,
            "auth_config": auth_config,
        })


# ========== 辅助函数 ==========

def _parse_kv_data(data):
    """解析 Key-Value 数据（可能是 JSON 字符串或列表）"""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return []
    if not isinstance(data, list):
        return []
    return data


def _extract_host(url):
    """从 URL 中提取 host 部分"""
    try:
        if "://" in url:
            rest = url.split("://", 1)[1]
        else:
            rest = url
        host_port = rest.split("/", 1)[0]
        host = host_port.split(":")[0]
        return host.split(".")
    except Exception:
        return [url]


def _extract_path(url):
    """从 URL 中提取 path 部分"""
    try:
        if "://" in url:
            rest = url.split("://", 1)[1]
        else:
            rest = url
        parts = rest.split("/", 1)
        if len(parts) > 1:
            path_str = parts[1].split("?", 1)[0].split("#", 1)[0]
            return [p for p in path_str.split("/") if p]
        return []
    except Exception:
        return []


def _parse_body_urlencoded(body_content):
    """解析 urlencoded body 为 Postman 格式"""
    items = []
    if not body_content:
        return items
    pairs = body_content.split("&")
    for pair in pairs:
        if "=" in pair:
            k, v = pair.split("=", 1)
            items.append({"key": k, "value": v, "type": "text"})
        else:
            items.append({"key": pair, "value": "", "type": "text"})
    return items


def _parse_body_formdata(body_content):
    """解析 formdata body 为 Postman 格式"""
    items = []
    if not body_content:
        return items
    try:
        data = json.loads(body_content) if isinstance(body_content, str) else body_content
        for d in data:
            items.append({
                "key": d.get("key", ""),
                "value": d.get("value", ""),
                "type": d.get("type", "text"),
                "disabled": not d.get("enabled", True),
            })
    except (json.JSONDecodeError, TypeError):
        pass
    return items


def _build_auth(auth_type, auth_config):
    """构建 Postman auth 对象"""
    if isinstance(auth_config, str):
        try:
            auth_config = json.loads(auth_config)
        except (json.JSONDecodeError, TypeError):
            auth_config = {}

    auth_type = auth_config.get("type", auth_type) if auth_config else auth_type

    if auth_type == "basic":
        return {
            "type": "basic",
            "basic": [
                {"key": "username", "value": auth_config.get("username", ""), "type": "string"},
                {"key": "password", "value": auth_config.get("password", ""), "type": "string"},
            ],
        }
    elif auth_type == "bearer":
        return {
            "type": "bearer",
            "bearer": [
                {"key": "token", "value": auth_config.get("token", ""), "type": "string"},
            ],
        }
    elif auth_type == "api_key":
        return {
            "type": "apikey",
            "apikey": [
                {"key": "key", "value": auth_config.get("key_name", "X-API-Key"), "type": "string"},
                {"key": "value", "value": auth_config.get("key_value", ""), "type": "string"},
                {"key": "in", "value": auth_config.get("add_to", "header"), "type": "string"},
            ],
        }
    return None