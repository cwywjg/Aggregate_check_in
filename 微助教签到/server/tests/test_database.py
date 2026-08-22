import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from models import database


class DatabaseMigrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await database.close_db()
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)

    async def asyncTearDown(self):
        await database.close_db()
        if os.path.exists(self.path):
            os.unlink(self.path)

    async def test_partial_keepalive_schema_adds_every_missing_column(self):
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "CREATE TABLE accounts_ext (ref TEXT PRIMARY KEY, keepalive_status TEXT DEFAULT 'unknown')"
            )

        with patch.object(database, "DB_PATH", self.path):
            await database.init_db()
            db = await database.get_db()
            cursor = await db.execute("PRAGMA table_info(accounts_ext)")
            columns = {row[1] for row in await cursor.fetchall()}

        self.assertIn("keepalive_status", columns)
        self.assertIn("last_keepalive_at", columns)
        self.assertIn("keepalive_fail_count", columns)


if __name__ == "__main__":
    unittest.main()
