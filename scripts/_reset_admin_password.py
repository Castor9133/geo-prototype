"""Force-reset the seeded admin password (dev helper)."""
from __future__ import annotations

import asyncio
import os
import sys

import bcrypt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import select

from app.core.database import async_session
from app.models.user import User, UserRole

NEW_PASSWORD = os.environ.get("GEORANK_RESET_ADMIN_PASSWORD", "Admin@123456")


async def main() -> None:
    async with async_session() as db:
        result = await db.execute(
            select(User).where(
                (User.username == "admin") | (User.email == "admin@georank.com")
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            print("ERROR: admin user not found")
            sys.exit(1)

        hashed = bcrypt.hashpw(NEW_PASSWORD.encode(), bcrypt.gensalt()).decode()
        user.hashed_password = hashed
        user.role = UserRole.ADMIN
        user.is_active = True
        user.is_verified = True
        user.username = "admin"
        if not user.email:
            user.email = "admin@georank.com"
        await db.commit()
        await db.refresh(user)

        ok = bcrypt.checkpw(NEW_PASSWORD.encode(), user.hashed_password.encode())
        print(
            f"OK username={user.username} email={user.email} role={user.role.value} "
            f"active={user.is_active} verify={ok} password={NEW_PASSWORD}"
        )


if __name__ == "__main__":
    asyncio.run(main())
