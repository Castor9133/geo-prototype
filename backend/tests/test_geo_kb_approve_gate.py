"""稿件过审闸门：审核岗 + 写≠审。"""
from __future__ import annotations

import asyncio
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.services import geo_kb as gkb


class FakeTask:
    def __init__(self, claimed_by=None, workflow_status="in_review"):
        self.id = uuid.uuid4()
        self.claimed_by = claimed_by
        self.reviewed_by = None
        self.workflow_status = workflow_status
        self.status = "pending"
        self.finished_at = None


class GeoKbApproveGateTests(unittest.TestCase):
    def test_reviewer_cannot_approve_own_claim(self):
        actor = SimpleNamespace(id=uuid.uuid4(), geo_role="reviewer", role="user")
        task = FakeTask(claimed_by=actor.id)

        async def run():
            db = AsyncMock()
            with self.assertRaises(PermissionError):
                await gkb.approve_ready(db, task, actor=actor)

        asyncio.run(run())

    def test_admin_cannot_business_approve(self):
        actor = SimpleNamespace(id=uuid.uuid4(), geo_role="admin", role="admin")
        task = FakeTask(claimed_by=uuid.uuid4())

        async def run():
            db = AsyncMock()
            with self.assertRaises(PermissionError):
                await gkb.approve_ready(db, task, actor=actor)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
