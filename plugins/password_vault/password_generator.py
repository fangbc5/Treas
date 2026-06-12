"""密码生成器模块"""

import random
import string


def generate_password(
    length: int = 16,
    use_uppercase: bool = True,
    use_lowercase: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
    exclude_ambiguous: bool = False,
) -> str:
    """生成随机密码

    Args:
        length: 密码长度（4-128）
        use_uppercase: 包含大写字母
        use_lowercase: 包含小写字母
        use_digits: 包含数字
        use_symbols: 包含特殊符号
        exclude_ambiguous: 排除易混淆字符 (0O1lI)

    Returns:
        生成的密码
    """
    length = max(4, min(128, length))

    chars = ""
    required = []

    if use_lowercase:
        pool = string.ascii_lowercase
        if exclude_ambiguous:
            pool = pool.replace("l", "")
        chars += pool
        required.append(random.choice(pool))

    if use_uppercase:
        pool = string.ascii_uppercase
        if exclude_ambiguous:
            pool = pool.replace("O", "").replace("I", "")
        chars += pool
        required.append(random.choice(pool))

    if use_digits:
        pool = string.digits
        if exclude_ambiguous:
            pool = pool.replace("0", "").replace("1", "")
        chars += pool
        required.append(random.choice(pool))

    if use_symbols:
        pool = "!@#$%^&*()-_=+[]{}|;:,.<>?"
        chars += pool
        required.append(random.choice(pool))

    if not chars:
        chars = string.ascii_letters + string.digits

    # 确保每种字符类型至少出现一次
    remaining = length - len(required)
    if remaining < 0:
        remaining = 0

    password = required + [random.choice(chars) for _ in range(remaining)]
    random.shuffle(password)
    return "".join(password)


def calculate_strength(password: str) -> dict:
    """计算密码强度

    Returns:
        {"score": 0-4, "label": str, "color": str}
    """
    if not password:
        return {"score": 0, "label": "无", "color": "#95a5a6"}

    score = 0
    length = len(password)

    # 长度评分
    if length >= 8:
        score += 1
    if length >= 12:
        score += 1
    if length >= 16:
        score += 1
    if length >= 24:
        score += 1

    # 字符多样性
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?" for c in password)

    diversity = sum([has_lower, has_upper, has_digit, has_symbol])
    score += max(0, diversity - 1)  # 至少2种才有加分

    # 重复字符惩罚
    unique_ratio = len(set(password)) / max(length, 1)
    if unique_ratio < 0.5:
        score -= 1

    score = max(0, min(4, score))

    labels = {
        0: ("极弱", "#e74c3c"),
        1: ("弱", "#e67e22"),
        2: ("中等", "#f1c40f"),
        3: ("强", "#2ecc71"),
        4: ("极强", "#27ae60"),
    }
    label, color = labels[score]

    return {"score": score, "label": label, "color": color}