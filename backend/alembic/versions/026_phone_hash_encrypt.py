"""手机号 HMAC 哈希 + 加宽密文列

Revision ID: 026_phone_hash_encrypt
Revises: 025_obs_white_accounts
Create Date: 2026-08-05
"""

from __future__ import annotations

import hashlib
import hmac
import os
import base64
import re

from alembic import op
import sqlalchemy as sa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

revision = "026_phone_hash_encrypt"
down_revision = "025_obs_white_accounts"
branch_labels = None
depends_on = None

PHONE_CIPHER_PREFIX = "ph1."
_AAD = b"user.phone"


def _settings_key() -> bytes:
    # 与 app.core.config.Settings.settings_encryption_key_bytes 对齐
    enc = (os.getenv("SETTINGS_ENCRYPTION_KEY") or "").strip()
    secret = (os.getenv("SECRET_KEY") or "change-me-in-production").strip()
    material = (enc or secret).encode("utf-8")
    return hashlib.sha256(material).digest()


def _normalize(phone: str) -> str | None:
    digits = re.sub(r"\D+", "", str(phone or ""))
    if digits.startswith("86") and len(digits) == 13:
        digits = digits[2:]
    if not re.fullmatch(r"1\d{10}", digits):
        return None
    return digits


def _hash(digits: str, key: bytes) -> str:
    return hmac.new(key, digits.encode("utf-8"), hashlib.sha256).hexdigest()


def _encrypt(digits: str, key: bytes) -> str:
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, digits.encode("utf-8"), _AAD)
    return (
        PHONE_CIPHER_PREFIX
        + base64.urlsafe_b64encode(nonce).decode("ascii").rstrip("=")
        + "."
        + base64.urlsafe_b64encode(ciphertext).decode("ascii").rstrip("=")
    )


def upgrade() -> None:
    op.add_column("users", sa.Column("phone_hash", sa.String(length=64), nullable=True))
    op.alter_column(
        "users",
        "phone",
        existing_type=sa.String(length=30),
        type_=sa.String(length=512),
        existing_nullable=True,
    )
    op.drop_index("ix_users_phone", table_name="users")

    conn = op.get_bind()
    key = _settings_key()
    rows = conn.execute(sa.text("SELECT id, phone FROM users WHERE phone IS NOT NULL")).fetchall()
    for row in rows:
        uid, phone = row[0], row[1]
        if not phone or str(phone).startswith(PHONE_CIPHER_PREFIX):
            continue
        digits = _normalize(str(phone))
        if not digits:
            continue
        conn.execute(
            sa.text(
                "UPDATE users SET phone = :phone, phone_hash = :phone_hash WHERE id = :id"
            ),
            {"phone": _encrypt(digits, key), "phone_hash": _hash(digits, key), "id": uid},
        )

    op.create_index("ix_users_phone_hash", "users", ["phone_hash"], unique=True)
    op.create_index("ix_users_phone", "users", ["phone"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_phone", table_name="users")
    op.drop_index("ix_users_phone_hash", table_name="users")
    op.drop_column("users", "phone_hash")
    op.alter_column(
        "users",
        "phone",
        existing_type=sa.String(length=512),
        type_=sa.String(length=30),
        existing_nullable=True,
    )
    op.create_index("ix_users_phone", "users", ["phone"], unique=True)
