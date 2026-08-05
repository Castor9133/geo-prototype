"""
手机号安全存储 — 落库加密 + HMAC 检索哈希。

- phone 列：AES-256-GCM 密文（或迁移前遗留明文，读时兼容）
- phone_hash 列：HMAC-SHA256，用于唯一约束与登录查找（不可逆）
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

PHONE_CIPHER_PREFIX = "ph1."
_AAD = b"user.phone"


def normalize_phone_digits(phone: str | None) -> str:
    digits = re.sub(r"\D+", "", str(phone or ""))
    if digits.startswith("86") and len(digits) == 13:
        digits = digits[2:]
    if not re.fullmatch(r"1\d{10}", digits):
        raise ValueError("请输入有效的手机号")
    return digits


def phone_lookup_hash(digits: str) -> str:
    key = settings.settings_encryption_key_bytes
    return hmac.new(key, digits.encode("utf-8"), hashlib.sha256).hexdigest()


def is_encrypted_phone(value: str | None) -> bool:
    return isinstance(value, str) and value.startswith(PHONE_CIPHER_PREFIX)


def encrypt_phone(digits: str) -> str:
    nonce = os.urandom(12)
    ciphertext = AESGCM(settings.settings_encryption_key_bytes).encrypt(
        nonce, digits.encode("utf-8"), _AAD
    )
    return (
        PHONE_CIPHER_PREFIX
        + base64.urlsafe_b64encode(nonce).decode("ascii").rstrip("=")
        + "."
        + base64.urlsafe_b64encode(ciphertext).decode("ascii").rstrip("=")
    )


def _b64url_decode(raw: str) -> bytes:
    pad = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + pad)


def decrypt_phone(stored: str | None) -> str | None:
    if not stored:
        return None
    if not is_encrypted_phone(stored):
        # 迁移前明文：若已是合法手机号则直接返回
        try:
            return normalize_phone_digits(stored)
        except ValueError:
            return None
    try:
        _, nonce_b64, ct_b64 = stored.split(".", 2)
        plaintext = AESGCM(settings.settings_encryption_key_bytes).decrypt(
            _b64url_decode(nonce_b64), _b64url_decode(ct_b64), _AAD
        )
        return plaintext.decode("utf-8")
    except Exception:
        return None


def mask_phone(digits: str | None) -> str | None:
    if not digits:
        return None
    if len(digits) < 7:
        return "****"
    return f"{digits[:3]}****{digits[-4:]}"


def assign_user_phone(user, plain: str | None) -> None:
    """写入 User.phone / User.phone_hash。plain 为 None 或空则清空。"""
    if plain is None or not str(plain).strip():
        user.phone = None
        user.phone_hash = None
        return
    digits = normalize_phone_digits(plain)
    user.phone_hash = phone_lookup_hash(digits)
    user.phone = encrypt_phone(digits)


def reveal_user_phone(user) -> str | None:
    return decrypt_phone(getattr(user, "phone", None))
