"""Excel 公式引擎 - 解析并执行类 Excel 公式"""

import re
from typing import Optional
from models import DataSourceConfig, RowContext, _to_number, _col_letter_to_index


class FormulaError(Exception):
    """公式错误"""
    pass


class FormulaEngine:
    """公式引擎

    支持的函数:
        VLOOKUP(lookup_value, source!range, col_index, [exact])
        SUMIF(source!criteria_range, criteria, source!sum_range)
        SUMIFS(source!sum_range, source!crit1_range, crit1, ...)
        COUNTIF(source!range, criteria)
        AVERAGEIF(source!crit_range, criteria, source!avg_range)
        MAXIFS(source!max_range, source!crit_range, criteria)
        MINIFS(source!min_range, source!crit_range, criteria)
        CONCATENATE(arg1, arg2, ...)
        ROUND(num, digits)
        ABS(num)
        LEN(text)
        IF(cond, true_val, false_val)
        SEQ(start_value) - 按行号自增(末尾数字+1，保持位数)
        SEARCH(find_text, within_text) - 文本包含判断，返回位置(0=未找到)
        LOOKUPI(lookup_value, source!lookup_col, source!return_col) - 包含匹配查找

    {字段名} 引用当前行已计算的前序字段值
    数据源名!A:D 引用数据源的列范围
    """

    # 已注册的数据源 {名称: DataSourceConfig}
    def __init__(self, data_sources: dict):
        self._sources = data_sources
        # 函数表
        self._functions = {
            "VLOOKUP": self._vlookup,
            "SUMIF": self._sumif,
            "SUMIFS": self._sumifs,
            "COUNTIF": self._countif,
            "AVERAGEIF": self._averageif,
            "MAXIFS": self._maxifs,
            "MINIFS": self._minifs,
            "CONCATENATE": self._concatenate,
            "ROUND": self._round,
            "ABS": self._abs,
            "LEN": self._len,
            "IF": self._if,
            "SUM": self._sum,
            "AVG": self._avg,
            "MAX": self._max,
            "MIN": self._min,
            "COUNT": self._count,
            "SEQ": self._seq,
            "SEARCH": self._search,
            "LOOKUPI": self._lookipi,
        }

    def evaluate(self, formula: str, ctx: RowContext):
        """执行公式，返回计算结果"""
        if not formula or not formula.strip():
            return ""
        expr = formula.strip()
        try:
            return self._eval_expr(expr, ctx)
        except FormulaError:
            raise
        except Exception as e:
            raise FormulaError(f"公式执行失败: {e}")

    def _eval_expr(self, expr: str, ctx: RowContext):
        """递归求值表达式"""
        expr = expr.strip()

        # 1. {字段引用}（单个字段引用，中间不能还有 {）
        if expr.startswith("{") and expr.endswith("}") and "{" not in expr[1:-1]:
            field = expr[1:-1].strip()
            val = ctx.get(field)
            if val is None:
                raise FormulaError(f"字段 '{field}' 未定义（可能需要调整字段顺序）")
            return val

        # 2. 布尔值 TRUE/FALSE
        upper = expr.upper()
        if upper == "TRUE":
            return True
        if upper == "FALSE":
            return False

        # 3. 字符串字面量 "xxx"
        if expr.startswith('"') and expr.endswith('"'):
            return expr[1:-1]

        # 4. 数字字面量
        num = _to_number(expr)
        if num is not None and re.match(r'^-?\d+\.?\d*$', expr):
            return num

        # 5. 函数调用 FUNC(...)
        m = re.match(r'^([A-Z]+)\s*\((.*)\)$', expr, re.IGNORECASE)
        if m:
            func_name = m.group(1).upper()
            args_str = m.group(2)
            args = self._split_args(args_str)
            func = self._functions.get(func_name)
            if not func:
                raise FormulaError(f"不支持的函数: {func_name}")
            return func(args, ctx)

        # 6. 算术/字符串表达式（含 + - * /）
        return self._eval_arithmetic(expr, ctx)

    def _split_args(self, args_str: str) -> list:
        """分割参数（考虑嵌套括号和引号）"""
        args = []
        depth = 0
        current = ""
        in_string = False
        for ch in args_str:
            if ch == '"' and not current.endswith("\\"):
                in_string = not in_string
                current += ch
            elif ch == "(" and not in_string:
                depth += 1
                current += ch
            elif ch == ")" and not in_string:
                depth -= 1
                current += ch
            elif ch == "," and depth == 0 and not in_string:
                args.append(current.strip())
                current = ""
            else:
                current += ch
        if current.strip():
            args.append(current.strip())
        return args

    def _eval_arithmetic(self, expr: str, ctx: RowContext):
        """求值含算术运算符和字段引用的表达式"""
        # 将 {字段} 替换为值
        def replace_field(m):
            fname = m.group(1).strip()
            val = ctx.get(fname)
            if val is None:
                return "0"
            return str(val)

        # 先处理嵌套函数（递归求值后替换为字面值）
        def replace_func(m):
            full = m.group(0)
            try:
                result = self._eval_expr(full, ctx)
                return str(result) if result is not None else "0"
            except Exception:
                return "0"

        processed = expr
        # 先替换函数调用（贪婪匹配嵌套）
        for _ in range(10):  # 最多10层嵌套
            new = re.sub(r'[A-Z]+\s*\([^()]*\)', replace_func, processed, flags=re.IGNORECASE)
            if new == processed:
                break
            processed = new

        # 替换字段引用
        processed = re.sub(r'\{([^}]+)\}', replace_field, processed)

        # 处理字符串拼接（+）
        if '"' in processed:
            return self._eval_string_concat(processed, ctx)

        # 纯算术
        try:
            # 安全检查：只允许数字、运算符、小数点、空格
            clean = processed.replace(" ", "")
            if not re.match(r'^[\d+\-*/().%><=]+$', clean):
                raise FormulaError(f"表达式包含非法字符: {expr}")
            return eval(clean, {"__builtins__": {}}, {})
        except FormulaError:
            raise
        except Exception as e:
            raise FormulaError(f"算术表达式错误 '{expr}': {e}")

    def _eval_string_concat(self, expr: str, ctx: RowContext):
        """字符串拼接求值"""
        parts = re.split(r'(\+)', expr)
        result = ""
        for part in parts:
            part = part.strip()
            if part == "+" or not part:
                continue
            if part.startswith('"') and part.endswith('"'):
                result += part[1:-1]
            else:
                val = ctx.get(part.strip("{}"))
                if val is None:
                    val = part
                result += str(val)
        return result

    def _parse_source_ref(self, ref: str) -> tuple:
        """解析 数据源名!A:D 或 数据源名!A 格式的引用

        返回: (DataSourceConfig, col_name)
        """
        if "!" not in ref:
            raise FormulaError(f"数据源引用需包含 '!' : {ref}")
        src_name, col_part = ref.split("!", 1)
        src_name = src_name.strip()
        # 去掉可能的引号
        if src_name.startswith('"') and src_name.endswith('"'):
            src_name = src_name[1:-1]

        src = self._sources.get(src_name)
        if not src:
            raise FormulaError(f"数据源 '{src_name}' 不存在")

        # col_part 可能是 A, A:A, A:B, B 等
        col_part = col_part.strip()
        # 只取第一列字母
        col_letter = col_part.split(":")[0].strip()
        col_name = src.find_column(col_letter)
        if not col_name:
            raise FormulaError(f"数据源 '{src_name}' 中找不到列 '{col_letter}'")
        return src, col_name

    # ── 函数实现 ──

    def _vlookup(self, args, ctx):
        """VLOOKUP(查找值, 数据源!范围, 返回列号, [精确匹配])"""
        if len(args) < 3:
            raise FormulaError("VLOOKUP 需要至少3个参数")
        lookup_val = self._eval_expr(args[0], ctx)
        src, _ = self._parse_source_ref(args[1])
        col_idx = int(self._eval_expr(args[2], ctx)) - 1
        exact = True
        if len(args) >= 4:
            ev = self._eval_expr(args[3], ctx)
            exact = (ev == 0 or ev == False or ev == "FALSE")

        for row in src.rows:
            first_val = row.get(src.columns[0]) if src.columns else None
            if str(first_val) == str(lookup_val):
                if 0 <= col_idx < len(src.columns):
                    return row.get(src.columns[col_idx])
        if not exact:
            # 近似匹配（排序后的最大较小值）— 简化处理
            pass
        return ""

    def _sumif(self, args, ctx):
        """SUMIF(条件范围, 条件, 求和范围)"""
        if len(args) < 3:
            raise FormulaError("SUMIF 需要3个参数")
        crit_src, crit_col = self._parse_source_ref(args[0])
        criteria = self._eval_expr(args[1], ctx)
        sum_src, sum_col = self._parse_source_ref(args[2])

        total = 0
        for row in crit_src.rows:
            if str(row.get(crit_col)) == str(criteria):
                v = _to_number(row.get(sum_col))
                if v is not None:
                    total += v
        return total

    def _sumifs(self, args, ctx):
        """SUMIFS(求和范围, 条件范围1, 条件1, ...)"""
        if len(args) < 3 or len(args) % 2 != 1:
            raise FormulaError("SUMIFS 参数数量错误")
        sum_src, sum_col = self._parse_source_ref(args[0])

        conditions = []
        for i in range(1, len(args), 2):
            cs, cc = self._parse_source_ref(args[i])
            cv = self._eval_expr(args[i + 1], ctx)
            conditions.append((cs, cc, str(cv)))

        total = 0
        for row in sum_src.rows:
            match = True
            for cs, cc, cv in conditions:
                if str(row.get(cc)) != cv:
                    match = False
                    break
            if match:
                v = _to_number(row.get(sum_col))
                if v is not None:
                    total += v
        return total

    def _countif(self, args, ctx):
        """COUNTIF(范围, 条件)"""
        if len(args) < 2:
            raise FormulaError("COUNTIF 需要2个参数")
        src, col = self._parse_source_ref(args[0])
        criteria = str(self._eval_expr(args[1], ctx))
        count = 0
        for row in src.rows:
            if str(row.get(col)) == criteria:
                count += 1
        return count

    def _averageif(self, args, ctx):
        """AVERAGEIF(条件范围, 条件, 平均范围)"""
        if len(args) < 3:
            raise FormulaError("AVERAGEIF 需要3个参数")
        crit_src, crit_col = self._parse_source_ref(args[0])
        criteria = self._eval_expr(args[1], ctx)
        avg_src, avg_col = self._parse_source_ref(args[2])
        vals = []
        for row in crit_src.rows:
            if str(row.get(crit_col)) == str(criteria):
                v = _to_number(row.get(avg_col))
                if v is not None:
                    vals.append(v)
        return sum(vals) / len(vals) if vals else 0

    def _maxifs(self, args, ctx):
        """MAXIFS(最大范围, 条件范围, 条件)"""
        if len(args) < 3:
            raise FormulaError("MAXIFS 需要3个参数")
        max_src, max_col = self._parse_source_ref(args[0])
        crit_src, crit_col = self._parse_source_ref(args[1])
        criteria = self._eval_expr(args[2], ctx)
        vals = []
        for row in max_src.rows:
            if str(row.get(crit_col)) == str(criteria):
                v = _to_number(row.get(max_col))
                if v is not None:
                    vals.append(v)
        return max(vals) if vals else 0

    def _minifs(self, args, ctx):
        """MINIFS(最小范围, 条件范围, 条件)"""
        if len(args) < 3:
            raise FormulaError("MINIFS 需要3个参数")
        min_src, min_col = self._parse_source_ref(args[0])
        crit_src, crit_col = self._parse_source_ref(args[1])
        criteria = self._eval_expr(args[2], ctx)
        vals = []
        for row in min_src.rows:
            if str(row.get(crit_col)) == str(criteria):
                v = _to_number(row.get(min_col))
                if v is not None:
                    vals.append(v)
        return min(vals) if vals else 0

    def _concatenate(self, args, ctx):
        return "".join(str(self._eval_expr(a, ctx) or "") for a in args)

    def _round(self, args, ctx):
        if len(args) < 1:
            raise FormulaError("ROUND 需要参数")
        num = _to_number(self._eval_expr(args[0], ctx)) or 0
        digits = int(self._eval_expr(args[1], ctx)) if len(args) >= 2 else 0
        return round(num, digits)

    def _abs(self, args, ctx):
        num = _to_number(self._eval_expr(args[0], ctx)) or 0
        return abs(num)

    def _len(self, args, ctx):
        return len(str(self._eval_expr(args[0], ctx) or ""))

    def _if(self, args, ctx):
        if len(args) < 3:
            raise FormulaError("IF 需要3个参数")
        cond = self._eval_expr(args[0], ctx)
        if cond:
            return self._eval_expr(args[1], ctx)
        return self._eval_expr(args[2], ctx)

    def _sum(self, args, ctx):
        vals = [self._eval_expr(a, ctx) for a in args]
        return sum(_to_number(v) or 0 for v in vals)

    def _avg(self, args, ctx):
        vals = [_to_number(self._eval_expr(a, ctx)) or 0 for a in args]
        return sum(vals) / len(vals) if vals else 0

    def _max(self, args, ctx):
        vals = [_to_number(self._eval_expr(a, ctx)) for a in args]
        vv = [v for v in vals if v is not None]
        return max(vv) if vv else 0

    def _min(self, args, ctx):
        vals = [_to_number(self._eval_expr(a, ctx)) for a in args]
        vv = [v for v in vals if v is not None]
        return min(vv) if vv else 0

    def _count(self, args, ctx):
        return len(args)

    def _seq(self, args, ctx):
        """SEQ(起始值): 按行号自增，递增末尾数字段，保持原始位数"""
        if len(args) < 1:
            raise FormulaError("SEQ 需要起始值参数")
        start = str(self._eval_expr(args[0], ctx))
        row_idx = ctx.get("_row_index") or 0
        m = re.search(r'(\d+)$', start)
        if not m:
            return start  # 末尾没数字，原样返回
        prefix = start[:m.start()]
        num_str = m.group(1)
        width = len(num_str)
        new_num = int(num_str) + row_idx
        return f"{prefix}{str(new_num).zfill(width)}"

    def _search(self, args, ctx):
        """SEARCH(找什么, 在哪找) - 文本包含判断

        返回找到的位置（从1开始），找不到返回0。
        在 IF 条件中，>0 为真，0 为假。
        """
        if len(args) < 2:
            raise FormulaError("SEARCH 需要2个参数")
        find_text = str(self._eval_expr(args[0], ctx) or "")
        within_text = str(self._eval_expr(args[1], ctx) or "")
        if not find_text:
            return 0
        idx = within_text.find(find_text)
        return idx + 1 if idx >= 0 else 0

    def _lookipi(self, args, ctx):
        """LOOKUPI(查找值, 数据源!查找列, 数据源!返回列) - 包含匹配查找

        在查找列中找第一个「包含」查找值的单元格，
        返回该行返回列的值。查找列和返回列可任意位置（不受列顺序限制）。
        找不到返回空字符串。
        """
        if len(args) < 3:
            raise FormulaError("LOOKUPI 需要3个参数")
        lookup_val = str(self._eval_expr(args[0], ctx) or "")
        if not lookup_val:
            return ""
        lookup_src, lookup_col = self._parse_source_ref(args[1])
        return_src, return_col = self._parse_source_ref(args[2])

        for row in lookup_src.rows:
            cell_val = str(row.get(lookup_col) or "")
            if lookup_val in cell_val:
                return row.get(return_col)
        return ""
