"""鉴权硬化与手机号加密单测（不依赖外部服务）。"""
from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-32chars!!")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-unit-32chars!!!")
os.environ.setdefault("SETTINGS_ENCRYPTION_KEY", "test-settings-enc-key-32chars!!!!!")


class PhoneSecurityTests(unittest.TestCase):
    def test_roundtrip_encrypt_and_hash(self):
        from app.services.phone_security import (
            assign_user_phone,
            encrypt_phone,
            decrypt_phone,
            normalize_phone_digits,
            phone_lookup_hash,
            reveal_user_phone,
        )

        digits = normalize_phone_digits("+86 138-0013-8000")
        self.assertEqual(digits, "13800138000")
        cipher = encrypt_phone(digits)
        self.assertTrue(cipher.startswith("ph1."))
        self.assertNotIn(digits, cipher)
        self.assertEqual(decrypt_phone(cipher), digits)
        self.assertEqual(len(phone_lookup_hash(digits)), 64)

        user = SimpleNamespace(phone=None, phone_hash=None)
        assign_user_phone(user, digits)
        self.assertTrue(user.phone.startswith("ph1."))
        self.assertEqual(user.phone_hash, phone_lookup_hash(digits))
        self.assertEqual(reveal_user_phone(user), digits)

    def test_legacy_plaintext_decrypt(self):
        from app.services.phone_security import decrypt_phone

        self.assertEqual(decrypt_phone("13900139000"), "13900139000")


class DepsNoAdminBypassTests(unittest.IsolatedAsyncioTestCase):
    async def test_optional_user_returns_none_without_token(self):
        from app.core import deps

        with patch.object(deps.settings, "GEORANK_ALLOW_ANONYMOUS_AI", True):
            user = await deps.get_current_user_optional(None, AsyncMock())
        self.assertIsNone(user)

    async def test_current_user_raises_401_without_token_even_if_anonymous_ai(self):
        from app.core import deps
        from fastapi import HTTPException

        with patch.object(deps.settings, "GEORANK_ALLOW_ANONYMOUS_AI", True):
            with self.assertRaises(HTTPException) as ctx:
                await deps.get_current_user(None, AsyncMock())
        self.assertEqual(ctx.exception.status_code, 401)

    async def test_require_admin_does_not_fall_back_to_demo_admin(self):
        from app.core import deps
        from fastapi import HTTPException

        db = AsyncMock()
        # 即便库里有管理员，无 token 也不得抬权
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = SimpleNamespace(
            role=deps.UserRole.ADMIN, is_active=True
        )
        db.execute = AsyncMock(return_value=mock_result)

        with patch.object(deps.settings, "GEORANK_ALLOW_ANONYMOUS_AI", True):
            with self.assertRaises(HTTPException) as ctx:
                await deps.get_current_user(None, db)
        self.assertEqual(ctx.exception.status_code, 401)


class ProductionSecurityGateTests(unittest.TestCase):
    def test_rejects_anonymous_ai_in_production(self):
        from app.core.config import Settings

        s = Settings(
            DEBUG=False,
            SECRET_KEY="a" * 32,
            JWT_SECRET="b" * 32,
            SETTINGS_ENCRYPTION_KEY="c" * 32,
            PUBLIC_BASE_URL="https://app.example.com",
            POSTGRES_PASSWORD="strong-postgres-password-1",
            GEORANK_ALLOW_ANONYMOUS_AI=True,
        )
        with self.assertRaises(RuntimeError) as ctx:
            s.validate_production_security()
        self.assertIn("GEORANK_ALLOW_ANONYMOUS_AI", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
