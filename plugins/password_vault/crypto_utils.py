"""加密工具模块 - 基于 Fernet 对称加密

使用 PBKDF2HMAC 从主密码派生密钥，Fernet (AES-128-CBC + HMAC) 加密密码字段。
"""

import os
import base64
import hashlib


def _get_cryptography():
    """延迟导入 cryptography 库"""
    try:
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        return Fernet, hashes, PBKDF2HMAC
    except ImportError:
        raise ImportError(
            "密码保险箱需要 cryptography 库，请点击「安装依赖」按钮安装"
        )


def generate_salt() -> str:
    """生成随机盐值（base64 编码）"""
    return base64.b64encode(os.urandom(16)).decode("utf-8")


def derive_key(master_password: str, salt: str) -> bytes:
    """从主密码派生加密密钥

    Args:
        master_password: 主密码明文
        salt: base64 编码的盐值

    Returns:
        Fernet 兼容的 32 字节密钥（url-safe base64 编码）
    """
    _, hashes, PBKDF2HMAC = _get_cryptography()

    salt_bytes = base64.b64decode(salt.encode("utf-8"))
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt_bytes,
        iterations=480000,  # OWASP 2023 推荐迭代次数
    )
    key = kdf.derive(master_password.encode("utf-8"))
    return base64.urlsafe_b64encode(key)


def hash_password(master_password: str, salt: str) -> str:
    """计算主密码的哈希值（用于验证，不可逆）

    Args:
        master_password: 主密码明文
        salt: base64 编码的盐值

    Returns:
        密码哈希（hex 编码）
    """
    salt_bytes = base64.b64decode(salt.encode("utf-8"))
    return hashlib.pbkdf2_hmac(
        "sha256",
        master_password.encode("utf-8"),
        salt_bytes,
        480000,
    ).hex()


def encrypt_password(plaintext: str, master_password: str, salt: str) -> str:
    """加密密码

    Args:
        plaintext: 密码明文
        master_password: 主密码
        salt: base64 编码的盐值

    Returns:
        加密后的密文（base64 编码的 Fernet token）
    """
    Fernet, _, _ = _get_cryptography()

    key = derive_key(master_password, salt)
    f = Fernet(key)
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_password(ciphertext: str, master_password: str, salt: str) -> str:
    """解密密码

    Args:
        ciphertext: 加密密文
        master_password: 主密码
        salt: base64 编码的盐值

    Returns:
        密码明文

    Raises:
        Exception: 主密码错误或数据损坏
    """
    Fernet, _, _ = _get_cryptography()

    key = derive_key(master_password, salt)
    f = Fernet(key)
    return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")


def verify_master_password(master_password: str, stored_hash: str, salt: str) -> bool:
    """验证主密码是否正确"""
    return hash_password(master_password, salt) == stored_hash