"""HTTP 请求执行引擎 - 处理请求构建、执行和变量替换"""

import json
import re
import time
import threading
from typing import Optional, Callable
from dataclasses import dataclass, field


@dataclass
class HttpRequest:
    """HTTP 请求数据模型"""
    method: str = "GET"
    url: str = ""
    headers: list = field(default_factory=list)       # [{"key": "", "value": "", "enabled": True}]
    params: list = field(default_factory=list)         # [{"key": "", "value": "", "enabled": True}]
    body_type: str = "none"  # none, json, form_data, urlencoded, raw
    body_content: str = ""
    auth_type: str = "none"  # none, basic, bearer, api_key
    auth_config: dict = field(default_factory=dict)


@dataclass
class HttpResponse:
    """HTTP 响应数据模型"""
    status_code: int = 0
    reason: str = ""
    elapsed_ms: float = 0
    size_bytes: int = 0
    headers: dict = field(default_factory=dict)
    body: str = ""
    error: str = ""
    content_type: str = ""

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def status_category(self) -> str:
        if self.error:
            return "error"
        if self.status_code == 0:
            return "none"
        cat = self.status_code // 100
        return {2: "success", 3: "redirect", 4: "client_error", 5: "server_error"}.get(cat, "unknown")

    @property
    def status_color(self) -> str:
        colors = {
            "success": "#27ae60",
            "redirect": "#f39c12",
            "client_error": "#e67e22",
            "server_error": "#e74c3c",
            "error": "#e74c3c",
            "none": "#999999",
            "unknown": "#999999",
        }
        return colors.get(self.status_category, "#999999")

    @property
    def formatted_size(self) -> str:
        if self.size_bytes < 1024:
            return f"{self.size_bytes} B"
        elif self.size_bytes < 1024 * 1024:
            return f"{self.size_bytes / 1024:.1f} KB"
        else:
            return f"{self.size_bytes / (1024 * 1024):.1f} MB"


class RequestEngine:
    """HTTP 请求引擎"""

    def __init__(self):
        self._variables: dict = {}  # 当前激活的环境变量
        self._session = None  # 当前请求的 session（用于取消）
        self._cancelled = False

    def set_variables(self, variables: dict):
        """设置当前环境变量"""
        self._variables = variables or {}

    def substitute_variables(self, text: str) -> str:
        """替换文本中的 {{variable}} 占位符"""
        if not text or not self._variables:
            return text

        def replacer(match):
            var_name = match.group(1).strip()
            return str(self._variables.get(var_name, match.group(0)))

        return re.sub(r'\{\{(\w+)\}\}', replacer, text)

    @staticmethod
    def find_unresolved_variables(text: str) -> list:
        """查找文本中所有未解析的 {{var}} 占位符"""
        if not text:
            return []
        return re.findall(r'\{\{(\s*\w+\s*)\}\}', text)

    def build_request_kwargs(self, request: HttpRequest) -> dict:
        """将 HttpRequest 构建为 requests 库的参数"""
        kwargs = {"timeout": 30, "allow_redirects": True}

        # 替换 URL 中的变量
        url = self.substitute_variables(request.url.strip())
        if not url:
            raise ValueError("URL 不能为空")

        # 检测 URL 中残留的未解析变量
        unresolved = self.find_unresolved_variables(url)
        if unresolved:
            var_list = "、".join(f"{{{{{v.strip()}}}}}" for v in unresolved)
            raise ValueError(
                f"变量 {var_list} 未在当前环境中定义（请检查环境变量设置或使用 {{变量名}} 语法）"
            )

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        # 查询参数
        params = {}
        for p in request.params:
            if p.get("enabled", True) and p.get("key"):
                params[self.substitute_variables(p["key"])] = self.substitute_variables(p.get("value", ""))
        if params:
            kwargs["params"] = params

        # 请求头
        headers = {}
        for h in request.headers:
            if h.get("enabled", True) and h.get("key"):
                headers[self.substitute_variables(h["key"])] = self.substitute_variables(h.get("value", ""))
        kwargs["headers"] = headers

        # 认证
        if request.auth_type == "basic":
            username = self.substitute_variables(request.auth_config.get("username", ""))
            password = self.substitute_variables(request.auth_config.get("password", ""))
            kwargs["auth"] = (username, password)
        elif request.auth_type == "bearer":
            token = self.substitute_variables(request.auth_config.get("token", ""))
            kwargs["headers"]["Authorization"] = f"Bearer {token}"
        elif request.auth_type == "api_key":
            key_name = request.auth_config.get("key_name", "X-API-Key")
            key_value = self.substitute_variables(request.auth_config.get("key_value", ""))
            add_to = request.auth_config.get("add_to", "header")
            if add_to == "header":
                kwargs["headers"][key_name] = key_value
            else:
                if "params" not in kwargs:
                    kwargs["params"] = {}
                kwargs["params"][key_name] = key_value

        # 请求体
        if request.method.upper() not in ("GET", "HEAD"):
            body_content = self.substitute_variables(request.body_content)
            if request.body_type == "json":
                kwargs["headers"].setdefault("Content-Type", "application/json")
                kwargs["data"] = body_content.encode("utf-8") if body_content else None
            elif request.body_type == "urlencoded":
                kwargs["headers"].setdefault("Content-Type", "application/x-www-form-urlencoded")
                if body_content:
                    form_data = {}
                    for line in body_content.split("&"):
                        if "=" in line:
                            k, v = line.split("=", 1)
                            form_data[k] = v
                    kwargs["data"] = form_data
            elif request.body_type == "form_data":
                # requests 会自动处理 multipart
                form_data = {}
                if body_content:
                    try:
                        items = json.loads(body_content)
                        for item in items:
                            if item.get("enabled", True) and item.get("key"):
                                form_data[item["key"]] = item.get("value", "")
                    except json.JSONDecodeError:
                        pass
                kwargs["files"] = None
                kwargs["data"] = form_data
            elif request.body_type == "raw":
                kwargs["data"] = body_content.encode("utf-8") if body_content else None

        return url, kwargs

    def execute(self, request: HttpRequest, callback: Optional[Callable] = None):
        """异步执行 HTTP 请求

        Args:
            request: 请求数据
            callback: 回调函数 callback(response: HttpResponse)
        """
        self._cancelled = False
        self._session = None
        thread = threading.Thread(
            target=self._execute_sync,
            args=(request, callback),
            daemon=True,
        )
        thread.start()

    def cancel(self):
        """取消当前进行中的请求"""
        self._cancelled = True
        if self._session:
            try:
                self._session.close()
            except Exception:
                pass
            self._session = None

    def _execute_sync(self, request: HttpRequest, callback: Optional[Callable] = None):
        """同步执行 HTTP 请求（支持取消）"""
        response = HttpResponse()
        try:
            self._execute_sync_inner(request, response)
        except Exception as e:
            if not response.error:
                response.error = f"内部错误: {e}"
        finally:
            self._session = None
        # 确保回调一定被调用（无论成功/失败/取消）
        if callback:
            callback(response)

    def _execute_sync_inner(self, request: HttpRequest, response: HttpResponse):
        """实际的请求执行逻辑（只填充 response，不调用 callback）"""
        import requests as req_lib

        if self._cancelled:
            response.error = "请求已取消"
            return

        try:
            url, kwargs = self.build_request_kwargs(request)
        except ValueError as e:
            response.error = str(e)
            return

        # 使用流式请求以便取消时能尽快中断
        kwargs["stream"] = True
        kwargs["timeout"] = (10, 30)  # (连接超时, 读取超时)

        try:
            session = req_lib.Session()
            self._session = session

            start_time = time.time()

            # 发送请求（连接 + 读取响应头阶段）
            resp = session.request(
                method=request.method.upper(),
                url=url,
                **kwargs,
            )

            if self._cancelled:
                resp.close()
                response.error = "请求已取消"
                return

            # 读取响应体
            try:
                content = resp.content  # 直接读取完整内容
            except req_lib.exceptions.Timeout:
                response.error = "读取响应超时"
                return
            except req_lib.exceptions.ConnectionError:
                response.error = "请求已取消" if self._cancelled else "连接中断"
                return

            if self._cancelled:
                resp.close()
                response.error = "请求已取消"
                return

            elapsed = (time.time() - start_time) * 1000

            response.status_code = resp.status_code
            response.reason = resp.reason or ""
            response.elapsed_ms = elapsed
            response.size_bytes = len(content)
            response.headers = dict(resp.headers)

            # 尝试解码文本
            encoding = resp.encoding or resp.apparent_encoding or "utf-8"
            try:
                response.body = content.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                response.body = content.decode("utf-8", errors="replace")
            response.content_type = resp.headers.get("Content-Type", "")

            resp.close()

        except req_lib.exceptions.Timeout:
            response.error = "请求已取消" if self._cancelled else "请求超时"
        except req_lib.exceptions.ConnectionError as e:
            response.error = "请求已取消" if self._cancelled else f"连接失败: {e}"
        except req_lib.exceptions.SSLError:
            response.error = "SSL 证书验证失败"
        except Exception as e:
            response.error = "请求已取消" if self._cancelled else f"请求异常: {e}"

    def execute_sync(self, request: HttpRequest) -> HttpResponse:
        """同步执行请求（阻塞）"""
        import requests as req_lib

        response = HttpResponse()

        try:
            url, kwargs = self.build_request_kwargs(request)
        except ValueError as e:
            response.error = str(e)
            return response

        try:
            start_time = time.time()
            resp = req_lib.request(
                method=request.method.upper(),
                url=url,
                **kwargs,
            )
            elapsed = (time.time() - start_time) * 1000

            response.status_code = resp.status_code
            response.reason = resp.reason or ""
            response.elapsed_ms = elapsed
            response.size_bytes = len(resp.content)
            response.headers = dict(resp.headers)
            response.body = resp.text
            response.content_type = resp.headers.get("Content-Type", "")

        except req_lib.exceptions.Timeout:
            response.error = "请求超时"
        except req_lib.exceptions.ConnectionError as e:
            response.error = f"连接失败: {e}"
        except Exception as e:
            response.error = f"请求异常: {e}"

        return response

    @staticmethod
    def format_json(text: str) -> str:
        """格式化 JSON 文本"""
        try:
            obj = json.loads(text)
            return json.dumps(obj, indent=2, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            return text

    @staticmethod
    def generate_code(request: HttpRequest, lang: str = "python") -> str:
        """根据请求生成代码

        Args:
            request: 请求数据
            lang: 目标语言 python / curl / fetch
        """
        method = request.method.upper()
        url = request.url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        if lang == "python":
            lines = [f"import requests", ""]
            lines.append(f'response = requests.{method.lower()}("{url}"')

            params = {p["key"]: p["value"] for p in request.params if p.get("enabled") and p.get("key")}
            if params:
                lines.append(f"    params={repr(params)}")

            headers = {h["key"]: h["value"] for h in request.headers if h.get("enabled") and h.get("key")}
            if headers:
                lines.append(f"    headers={repr(headers)}")

            if method not in ("GET", "HEAD") and request.body_content:
                if request.body_type == "json":
                    lines.append(f'    json={request.body_content}')
                else:
                    lines.append(f'    data={repr(request.body_content)}')

            if request.auth_type == "basic":
                lines.append(f'    auth=({repr(request.auth_config.get("username", ""))}, '
                             f'{repr(request.auth_config.get("password", ""))})')

            code = ",\n".join(lines) + ")"
            code += f"\n\nprint(response.status_code)\nprint(response.json())"
            return code

        elif lang == "curl":
            parts = [f"curl -X {method}"]

            for h in request.headers:
                if h.get("enabled") and h.get("key"):
                    parts.append(f'-H "{h["key"]}: {h["value"]}"')

            if request.auth_type == "bearer":
                parts.append(f'-H "Authorization: Bearer {request.auth_config.get("token", "")}"')
            elif request.auth_type == "basic":
                import base64
                cred = base64.b64encode(
                    f'{request.auth_config.get("username", "")}:{request.auth_config.get("password", "")}'.encode()
                ).decode()
                parts.append(f'-H "Authorization: Basic {cred}"')

            if method not in ("GET", "HEAD") and request.body_content:
                body = request.body_content.replace('"', '\\"')
                parts.append(f'-d "{body}"')

            parts.append(f'"{url}"')
            return " \\\n  ".join(parts)

        elif lang == "fetch":
            options = [f'  method: "{method}"']

            headers = {h["key"]: h["value"] for h in request.headers if h.get("enabled") and h.get("key")}
            if headers:
                options.append(f"  headers: {json.dumps(headers, indent=4)}")

            if method not in ("GET", "HEAD") and request.body_content:
                if request.body_type == "json":
                    options.append(f"  body: JSON.stringify({request.body_content})")
                else:
                    options.append(f"  body: {repr(request.body_content)}")

            opts_str = ",\n".join(options)
            return f'fetch("{url}", {{\n{opts_str}\n}})\n  .then(res => res.json())\n  .then(data => console.log(data))'

        return ""