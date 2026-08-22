import time
import unittest
from unittest.mock import AsyncMock, patch

from services.keepalive import refresh_tm_sessions_once


class FakeTMSession:
    def __init__(self, expires_after_ensure):
        self.expires_at = 0
        self.expires_after_ensure = expires_after_ensure
        self.ensure_session = AsyncMock(side_effect=self._ensure)
        self.refresh_session = AsyncMock(side_effect=self._refresh)

    async def _ensure(self):
        self.expires_at = int(time.time()) + self.expires_after_ensure

    async def _refresh(self, force=False):
        self.expires_at = int(time.time()) + 24 * 3600


class KeepaliveTests(unittest.IsolatedAsyncioTestCase):
    async def test_tm_round_loads_persisted_session_before_expiry_decision(self):
        session = FakeTMSession(12 * 3600)
        with (
            patch("services.keepalive.get_all_account_exts", new=AsyncMock(return_value=[{"ref": "A"}])),
            patch("services.keepalive.get_tm_session", return_value=session),
        ):
            result = await refresh_tm_sessions_once()

        session.ensure_session.assert_awaited_once()
        session.refresh_session.assert_not_awaited()
        self.assertEqual(result["validated"], 1)

    async def test_tm_round_refreshes_cookie_inside_two_hour_window(self):
        session = FakeTMSession(60 * 60)
        with (
            patch("services.keepalive.get_all_account_exts", new=AsyncMock(return_value=[{"ref": "A"}])),
            patch("services.keepalive.get_tm_session", return_value=session),
        ):
            result = await refresh_tm_sessions_once()

        session.refresh_session.assert_awaited_once_with(force=True)
        self.assertEqual(result["refreshed"], 1)


if __name__ == "__main__":
    unittest.main()
