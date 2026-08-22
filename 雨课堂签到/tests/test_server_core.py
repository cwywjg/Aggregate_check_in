import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

_TEMP_DIR = tempfile.TemporaryDirectory()
os.environ["YKT_DATA_DIR"] = _TEMP_DIR.name
os.environ["YKT_ADMIN_KEY"] = "test-admin-key-with-sufficient-length"
os.environ["YKT_ENABLE_AI_SELF_TEST"] = "0"

from safe_json_store import (  # noqa: E402
    ACCOUNTS_STORE,
    AI_HEALTH_STORE,
    HISTORY_STORE,
    KEYS_STORE,
    PROBLEM_STATE_STORE,
    JsonStore,
)
import api_server  # noqa: E402
from api_server import app  # noqa: E402
import ai_solver  # noqa: E402
import ykt_monitor  # noqa: E402


def tearDownModule():
    logging.shutdown()
    _TEMP_DIR.cleanup()


class JsonStoreTests(unittest.TestCase):
    def test_concurrent_updates_are_not_lost(self):
        store = JsonStore(Path(_TEMP_DIR.name) / "concurrency.json", list)
        worker_count = 24

        def worker(index):
            store.update(lambda rows: rows.append(index))

        threads = [threading.Thread(target=worker, args=(index,)) for index in range(worker_count)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sorted(store.read()), list(range(worker_count)))

    def test_concurrent_process_updates_are_not_lost(self):
        path = Path(_TEMP_DIR.name) / "multiprocess.json"
        worker_count = 12
        processes = []
        for index in range(worker_count):
            code = (
                f"import sys;sys.path.insert(0,{str(PROJECT_ROOT)!r});"
                "from safe_json_store import JsonStore;"
                f"s=JsonStore({str(path)!r},list);"
                f"s.update(lambda rows: rows.append({index}))"
            )
            processes.append(subprocess.Popen([sys.executable, "-c", code]))
        exit_codes = [process.wait() for process in processes]
        self.assertTrue(all(code == 0 for code in exit_codes))
        self.assertEqual(sorted(json.loads(path.read_text(encoding="utf-8"))), list(range(worker_count)))


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        ACCOUNTS_STORE.write([])
        KEYS_STORE.write({})
        AI_HEALTH_STORE.write({})
        HISTORY_STORE.write([])
        PROBLEM_STATE_STORE.write({})
        with api_server.RATE_LOCK:
            api_server.RATE_WINDOWS.clear()
        self.admin = {"Authorization": os.environ["YKT_ADMIN_KEY"]}
        self.key_a = "tenant_A_1234567890"
        self.key_b = "tenant_B_1234567890"
        for key in (self.key_a, self.key_b):
            response = self.client.post(
                "/api/sync/create_key",
                headers=self.admin,
                json={"key": key, "remark": key},
            )
            self.assertEqual(response.status_code, 200)

    def test_unregistered_key_is_rejected(self):
        response = self.client.get("/api/sync/download", headers={"Authorization": "random-key-12345"})
        self.assertEqual(response.status_code, 403)

    def test_registered_key_is_not_charged_to_unknown_ip_bucket(self):
        statuses = [
            self.client.get(
                "/api/sync/profile",
                headers={"Authorization": self.key_a},
            ).status_code
            for _ in range(65)
        ]
        self.assertEqual(set(statuses), {200})

    def test_admin_routes_require_admin_key(self):
        response = self.client.post(
            "/api/sync/create_key",
            headers={"Authorization": self.key_a},
            json={"key": "another-key-123456", "remark": "x"},
        )
        self.assertEqual(response.status_code, 403)

    def test_short_simple_key_and_profile_are_supported(self):
        simple_key = "1"
        created = self.client.post(
            "/api/sync/create_key",
            headers=self.admin,
            json={"key": simple_key, "remark": "简单密钥"},
        )
        self.assertEqual(created.status_code, 200)
        profile = self.client.get("/api/sync/profile", headers={"Authorization": simple_key})
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.get_json()["data"]["remark"], "简单密钥")

    def test_admin_password_cannot_be_created_as_tenant_key(self):
        response = self.client.post(
            "/api/sync/create_key",
            headers=self.admin,
            json={"key": os.environ["YKT_ADMIN_KEY"], "remark": "reserved"},
        )
        self.assertEqual(response.status_code, 409)

    def test_key_update_preserves_tenant_data(self):
        uploaded = self.client.post(
            "/api/sync/upload",
            headers={"Authorization": self.key_a},
            json={"accounts": [{"phone": "13900000000", "cookie": "x=1"}]},
        )
        self.assertEqual(uploaded.status_code, 200)
        listed = self.client.get("/api/sync/keys", headers=self.admin)
        self.assertEqual(listed.status_code, 200)
        key_record = next(item for item in listed.get_json()["data"] if item["remark"] == self.key_a)
        updated = self.client.post(
            "/api/sync/update_key",
            headers=self.admin,
            json={"key_id": key_record["id"], "new_key": "new", "remark": "更新后"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(
            self.client.get("/api/sync/download", headers={"Authorization": self.key_a}).status_code,
            403,
        )
        downloaded = self.client.get("/api/sync/download", headers={"Authorization": "new"})
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded.get_json()["data"][0]["phone"], "13900000000")

    def test_upload_preserves_expired_and_tenant_isolation(self):
        first = self.client.post(
            "/api/sync/upload",
            headers={"Authorization": self.key_a},
            json={
                "accounts": [
                    {
                        "phone": "13800000000",
                        "cookie": "a=1",
                        "expired": True,
                        "validityState": "expired",
                        "validityCheckedAt": 100,
                    }
                ]
            },
        )
        self.assertEqual(first.status_code, 200)
        second = self.client.post(
            "/api/sync/upload",
            headers={"Authorization": self.key_a},
            json={"accounts": [{"phone": "13800000000", "remark": "patched"}]},
        )
        self.assertEqual(second.status_code, 200)
        own = self.client.get("/api/sync/download", headers={"Authorization": self.key_a}).get_json()["data"]
        other = self.client.get("/api/sync/download", headers={"Authorization": self.key_b}).get_json()["data"]
        self.assertEqual(len(own), 1)
        self.assertTrue(own[0]["expired"])
        self.assertEqual(own[0]["cookie"], "a=1")
        self.assertEqual(own[0]["remark"], "patched")
        self.assertEqual(other, [])

    def test_stale_or_unknown_validity_cannot_erase_explicit_expiry(self):
        expired = self.client.post(
            "/api/sync/upload",
            headers={"Authorization": self.key_a},
            json={
                "accounts": [{
                    "phone": "13800000009",
                    "expired": True,
                    "validityState": "expired",
                    "validitySource": "server-monitor",
                    "validityCheckedAt": 500,
                    "validityFailureCount": 2,
                }],
            },
        )
        self.assertEqual(expired.status_code, 200)
        unknown = self.client.post(
            "/api/sync/upload",
            headers={"Authorization": self.key_a},
            json={
                "accounts": [{
                    "phone": "13800000009",
                    "expired": False,
                    "validityState": "unknown",
                    "validitySource": "local",
                    "validityCheckedAt": 600,
                }],
            },
        )
        self.assertEqual(unknown.status_code, 200)
        row = self.client.get(
            "/api/sync/download",
            headers={"Authorization": self.key_a},
        ).get_json()["data"][0]
        self.assertTrue(row["expired"])
        self.assertEqual(row["validityState"], "expired")
        self.assertEqual(row["validitySource"], "server-monitor")
        self.assertEqual(row["validityCheckedAt"], 500)

    def test_lesson_credentials_use_atomic_versioned_merge(self):
        first = self.client.post(
            "/api/sync/upload",
            headers={"Authorization": self.key_a},
            json={
                "accounts": [
                    {
                        "phone": "13700000000",
                        "lessonId": "9527",
                        "lessonToken": "new-token",
                        "lessonContext": {"id": "9527", "courseName": "高等数学"},
                        "lessonCredentialUpdatedAt": 200,
                    }
                ]
            },
        )
        self.assertEqual(first.status_code, 200)

        stale = self.client.post(
            "/api/sync/upload",
            headers={"Authorization": self.key_a},
            json={
                "accounts": [
                    {
                        "phone": "13700000000",
                        "lessonId": "",
                        "lessonToken": "",
                        "lessonContext": None,
                        "lessonCredentialUpdatedAt": 100,
                    }
                ]
            },
        )
        self.assertEqual(stale.status_code, 200)
        row = self.client.get(
            "/api/sync/download",
            headers={"Authorization": self.key_a},
        ).get_json()["data"][0]
        self.assertEqual(row["lessonToken"], "new-token")
        self.assertEqual(row["lessonId"], "9527")

        enriched = self.client.post(
            "/api/sync/upload",
            headers={"Authorization": self.key_a},
            json={
                "accounts": [
                    {
                        "phone": "13700000000",
                        "lessonId": "9527",
                        "lessonToken": "new-token",
                        "lessonContext": {
                            "id": "9527",
                            "courseName": "高等数学",
                            "lessonTitle": "第一章",
                            "wssUrl": "wss://changjiang.yuketang.cn/wsapp/",
                        },
                        "lessonCredentialUpdatedAt": 200,
                    }
                ]
            },
        )
        self.assertEqual(enriched.status_code, 200)
        row = self.client.get(
            "/api/sync/download",
            headers={"Authorization": self.key_a},
        ).get_json()["data"][0]
        self.assertEqual(row["lessonToken"], "new-token")
        self.assertEqual(row["lessonContext"]["courseName"], "高等数学")

        cleared = self.client.post(
            "/api/sync/upload",
            headers={"Authorization": self.key_a},
            json={
                "accounts": [
                    {
                        "phone": "13700000000",
                        "lessonId": "",
                        "lessonToken": "",
                        "lessonContext": None,
                        "lessonCredentialUpdatedAt": 300,
                    }
                ]
            },
        )
        self.assertEqual(cleared.status_code, 200)
        row = self.client.get(
            "/api/sync/download",
            headers={"Authorization": self.key_a},
        ).get_json()["data"][0]
        self.assertEqual(row["lessonToken"], "")
        self.assertEqual(row["lessonCredentialUpdatedAt"], 300)

    def test_client_deletion_tombstone_is_ignored_by_default(self):
        for key in (self.key_a, self.key_b):
            response = self.client.post(
                "/api/sync/upload",
                headers={"Authorization": key},
                json={"accounts": [{"phone": "13600000000", "remark": key}]},
            )
            self.assertEqual(response.status_code, 200)

        deleted = self.client.post(
            "/api/sync/upload",
            headers={"Authorization": self.key_a},
            json={
                "accounts": [],
                "deleted_accounts": [{"phone": "13600000000"}],
            },
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.get_json()["deleted"], 0)
        self.assertEqual(deleted.get_json()["ignored_deletions"], 1)
        own = self.client.get(
            "/api/sync/download",
            headers={"Authorization": self.key_a},
        ).get_json()["data"]
        other = self.client.get(
            "/api/sync/download",
            headers={"Authorization": self.key_b},
        ).get_json()["data"]
        self.assertEqual(len(own), 1)
        self.assertEqual(len(other), 1)

    def test_remote_account_delete_requires_explicit_server_opt_in(self):
        uploaded = self.client.post(
            "/api/sync/upload",
            headers={"Authorization": self.key_a},
            json={"accounts": [{"phone": "13600000001"}]},
        )
        self.assertEqual(uploaded.status_code, 200)
        with mock.patch.object(api_server, "ALLOW_REMOTE_ACCOUNT_DELETE", True):
            deleted = self.client.post(
                "/api/sync/upload",
                headers={"Authorization": self.key_a},
                json={
                    "accounts": [],
                    "deleted_accounts": [{"phone": "13600000001"}],
                },
            )
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.get_json()["deleted"], 1)

    def test_deleting_key_purges_tenant_secrets_and_history(self):
        uploaded = self.client.post(
            "/api/sync/upload",
            headers={"Authorization": self.key_a},
            json={"accounts": [{"phone": "13500000000", "cookie": "sessionid=secret"}]},
        )
        self.assertEqual(uploaded.status_code, 200)
        tenant_id = self.client.get(
            "/api/sync/profile",
            headers={"Authorization": self.key_a},
        ).get_json()["data"]["tenant_id"]
        HISTORY_STORE.write([{"groupKey": tenant_id, "id": "history-secret"}])
        PROBLEM_STATE_STORE.write(
            {"state-secret": {"groupKey": tenant_id, "status": "processing"}}
        )

        listed = self.client.get("/api/sync/keys", headers=self.admin).get_json()["data"]
        key_record = next(item for item in listed if item["remark"] == self.key_a)
        deleted = self.client.post(
            "/api/sync/delete_key",
            headers=self.admin,
            json={"key_id": key_record["id"]},
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.get_json()["purged"]["accounts"], 1)
        self.assertEqual(ACCOUNTS_STORE.read(), [])
        self.assertEqual(HISTORY_STORE.read(), [])
        self.assertEqual(PROBLEM_STATE_STORE.read(), {})

    def test_mismatched_key_and_key_id_cannot_delete_two_tenants(self):
        listed = self.client.get("/api/sync/keys", headers=self.admin).get_json()["data"]
        key_a_id = next(item["id"] for item in listed if item["remark"] == self.key_a)
        response = self.client.post(
            "/api/sync/delete_key",
            headers=self.admin,
            json={"key": self.key_b, "key_id": key_a_id},
        )
        self.assertEqual(response.status_code, 409)
        for key in (self.key_a, self.key_b):
            self.assertEqual(
                self.client.get(
                    "/api/sync/profile",
                    headers={"Authorization": key},
                ).status_code,
                200,
            )

    def test_private_image_url_is_rejected_before_fetch(self):
        response = self.client.post(
            "/api/ai/solve",
            headers={"Authorization": self.key_a},
            json={
                "problem_type": 0,
                "body": "x",
                "options": [{"key": "A", "value": "a"}],
                "image_url": "http://127.0.0.1:5000/private",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("image rejected", response.get_json()["msg"])

    def test_ai_history_preserves_provider_and_model(self):
        record_id = "route-metadata-test"
        written = self.client.post(
            "/api/ai/history/record",
            headers={"Authorization": self.key_a},
            json={
                "id": record_id,
                "problemId": "p1",
                "problemType": "单选题",
                "aiAnswer": ["A"],
                "aiProvider": "siliconflow",
                "aiModel": "Qwen/Qwen3.5-27B",
            },
        )
        self.assertEqual(written.status_code, 200)
        payload = self.client.get(
            "/api/ai/history",
            headers={"Authorization": self.key_a},
        ).get_json()
        record = next(item for item in payload["data"] if item["id"] == record_id)
        self.assertEqual(record["aiProvider"], "siliconflow")
        self.assertEqual(record["aiModel"], "Qwen/Qwen3.5-27B")
        self.assertEqual(payload["ai_status"]["model"], "Qwen/Qwen3.5-27B")

    def test_ai_history_exposes_latest_gemma_health_record(self):
        record = {
            "success": True,
            "status": "success",
            "provider": "nvidia",
            "model": "google/gemma-4-31b-it",
            "displayName": "Gemma-4",
            "prompt": "你好",
            "checkedAt": 1785031200000,
            "checkedAtText": "2026-07-26 09:00:00",
            "elapsedSeconds": 1.25,
            "error": "",
        }
        AI_HEALTH_STORE.write(
            {
                "latest": record,
                "history": [record],
                "intervalSeconds": 10800,
            }
        )
        payload = self.client.get(
            "/api/ai/history",
            headers={"Authorization": self.key_a},
        ).get_json()
        self.assertEqual(payload["ai_health"]["latest"]["prompt"], "你好")
        self.assertTrue(payload["ai_status"]["ready"])
        self.assertEqual(payload["ai_status"]["msg"], "成功")
        self.assertEqual(payload["ai_status"]["model"], "google/gemma-4-31b-it")


class AiProviderConfigTests(unittest.TestCase):
    def test_answer_validation_respects_blank_and_vote_cardinality(self):
        self.assertEqual(
            ai_solver.validate_answers(
                3,
                ["甲", "乙"],
                [],
                blank_count=2,
            ),
            ["甲", "乙"],
        )
        with self.assertRaises(ValueError):
            ai_solver.validate_answers(3, ["甲"], [], blank_count=2)
        self.assertEqual(
            ai_solver.validate_answers(
                2,
                ["A", "B"],
                [{"key": "A"}, {"key": "B"}],
                max_select=2,
            ),
            ["A", "B"],
        )
        with self.assertRaises(ValueError):
            ai_solver.validate_answers(
                2,
                ["A", "B"],
                [{"key": "A"}, {"key": "B"}],
                max_select=1,
            )
    def test_connectivity_probe_uses_only_gemma_without_thinking(self):
        with mock.patch.object(
            ai_solver,
            "_call_ai_route",
            return_value=("你好，我在线。", "google/gemma-4-31b-it"),
        ) as call:
            record = ai_solver.check_ai_connectivity(timeout_seconds=5)
        self.assertTrue(record["success"])
        self.assertEqual(record["prompt"], "你好")
        self.assertEqual(record["provider"], "nvidia")
        self.assertEqual(record["model"], "google/gemma-4-31b-it")
        call.assert_called_once_with(
            "你好",
            None,
            "nvidia",
            "google/gemma-4-31b-it",
            5,
            False,
            64,
        )

    def test_monitor_persists_dual_health_history(self):
        AI_HEALTH_STORE.write({})
        record = {
            "success": True,
            "status": "success",
            "provider": "nvidia",
            "model": "google/gemma-4-31b-it",
            "displayName": "Gemma-4",
            "tone": "blue",
            "prompt": "你好",
            "checkedAt": 1785031200000,
            "checkedAtText": "09:00:00",
            "elapsedSeconds": 0.8,
            "responsePreview": "你好",
            "error": "",
        }
        with mock.patch.object(
            ykt_monitor,
            "check_ai_connectivity",
            return_value=dict(record),
        ) as probe:
            saved = ykt_monitor.check_ai_health()
        self.assertEqual(probe.call_count, 2)
        persisted = AI_HEALTH_STORE.read()
        self.assertTrue(saved["success"])
        self.assertEqual(persisted["latest"]["prompt"], "你好")
        self.assertEqual(len(persisted["probes"]), 2)
        self.assertEqual(persisted["intervalSeconds"], 10800)
        self.assertEqual(len(persisted["history"]), 2)

    def test_siliconflow_provider_has_safe_defaults(self):
        env = os.environ.copy()
        env.update(
            {
                "AI_PROVIDER": "siliconflow",
                "AI_API_KEY": "",
                "AI_MODELS": "",
                "SILICONFLOW_API_KEY": "test-only-key",
                "SILICONFLOW_MODELS": "Qwen/Qwen3.5-27B",
            }
        )
        code = (
            "import json,ai_solver;"
            "print(json.dumps(ai_solver.get_ai_runtime_info()))"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        runtime = json.loads(result.stdout)
        self.assertEqual(runtime["provider"], "siliconflow")
        self.assertEqual(runtime["models"], ["Qwen/Qwen3.5-27B"])
        self.assertEqual(runtime["base_url"], "https://api.siliconflow.cn/v1")
        self.assertTrue(runtime["configured"])

    def test_cloudflare_provider_has_safe_defaults(self):
        env = os.environ.copy()
        env.update(
            {
                "AI_PROVIDER": "cloudflare",
                "AI_API_KEY": "",
                "AI_MODELS": "",
                "CLOUDFLARE_API_KEY": "test-cf-token",
                "CLOUDFLARE_ACCOUNT_ID": "d1d9ce08f8644dfe7bf177551f503a13",
                "CLOUDFLARE_MODELS": "@cf/qwen/qwen3.8-27b",
            }
        )
        code = (
            "import json,ai_solver;"
            "print(json.dumps(ai_solver.get_ai_runtime_info()))"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        runtime = json.loads(result.stdout)
        self.assertEqual(runtime["provider"], "cloudflare")
        self.assertEqual(runtime["models"], ["@cf/qwen/qwen3.8-27b"])
        self.assertEqual(
            runtime["base_url"],
            "https://api.cloudflare.com/client/v4/accounts/d1d9ce08f8644dfe7bf177551f503a13/ai/v1",
        )
        self.assertTrue(runtime["configured"])

    def test_phase1_simultaneous_parallel_consensus(self):
        routes = [
            {
                "provider": "nvidia",
                "model": "google/gemma-4-31b-it",
                "configured": True,
            },
            {
                "provider": "cloudflare",
                "model": "@cf/qwen/qwen3.8-27b",
                "configured": True,
            },
            {
                "provider": "siliconflow",
                "model": "Qwen/Qwen3.5-27B",
                "configured": True,
            },
        ]
        calls = []

        def fake_call(_prompt, _image, provider, model, _timeout, thinking):
            calls.append((provider, model, thinking))
            return '{"answers":["A"]}', model

        with mock.patch.object(ai_solver, "get_ai_routes", return_value=routes), mock.patch.object(
            ai_solver,
            "_call_ai_route",
            side_effect=fake_call,
        ):
            answers, error, metadata = ai_solver.solve_yuketang_problem_with_metadata(
                0,
                "测试题",
                [{"key": "A", "value": "正确"}, {"key": "B", "value": "错误"}],
                timeout_seconds=25,
                thinking_timeout_seconds=25,
            )
        self.assertEqual(error, "")
        self.assertEqual(answers, ["A"])
        self.assertEqual({c[0] for c in calls}, {"nvidia", "cloudflare"})
        self.assertTrue(metadata["fastConsensus"])
        self.assertEqual(metadata["targetSubmitDelaySeconds"], 35.0)

    def test_phase1_simultaneous_parallel_disagreement_prefers_qwen38(self):
        routes = [
            {
                "provider": "nvidia",
                "model": "google/gemma-4-31b-it",
                "configured": True,
            },
            {
                "provider": "cloudflare",
                "model": "@cf/qwen/qwen3.8-27b",
                "configured": True,
            },
            {
                "provider": "siliconflow",
                "model": "Qwen/Qwen3.5-27B",
                "configured": True,
            },
        ]

        def fake_call(_prompt, _image, provider, model, _timeout, _thinking):
            if provider == "nvidia":
                return '{"answers":["A"]}', model
            if provider == "cloudflare":
                return '{"answers":["B"]}', model
            return '{"answers":["C"]}', model

        with mock.patch.object(ai_solver, "get_ai_routes", return_value=routes), mock.patch.object(
            ai_solver,
            "_call_ai_route",
            side_effect=fake_call,
        ):
            answers, error, metadata = ai_solver.solve_yuketang_problem_with_metadata(
                0,
                "测试题",
                [{"key": "A", "value": "NVIDIA答案"}, {"key": "B", "value": "Cloudflare答案"}],
                timeout_seconds=25,
                thinking_timeout_seconds=25,
            )
        self.assertEqual(error, "")
        self.assertEqual(answers, ["B"])
        self.assertFalse(metadata["fastConsensus"])
        self.assertEqual(metadata["provider"], "cloudflare")
        self.assertEqual(metadata["model"], "@cf/qwen/qwen3.8-27b")
        self.assertEqual(metadata["targetSubmitDelaySeconds"], 35.0)

    def test_phase2_fallback_to_siliconflow_when_phase1_fails(self):
        routes = [
            {
                "provider": "nvidia",
                "model": "google/gemma-4-31b-it",
                "configured": True,
            },
            {
                "provider": "cloudflare",
                "model": "@cf/qwen/qwen3.8-27b",
                "configured": True,
            },
            {
                "provider": "siliconflow",
                "model": "Qwen/Qwen3.5-27B",
                "configured": True,
            },
        ]

        def fake_call(_prompt, _image, provider, model, _timeout, _thinking):
            if provider in {"nvidia", "cloudflare"}:
                raise TimeoutError(f"simulated {provider} timeout")
            return '{"answers":["C"]}', model

        with mock.patch.object(ai_solver, "get_ai_routes", return_value=routes), mock.patch.object(
            ai_solver,
            "_call_ai_route",
            side_effect=fake_call,
        ):
            answers, error, metadata = ai_solver.solve_yuketang_problem_with_metadata(
                0,
                "测试题",
                [{"key": "A", "value": "A"}, {"key": "B", "value": "B"}, {"key": "C", "value": "C"}],
                timeout_seconds=50,
                thinking_timeout_seconds=25,
            )
        self.assertEqual(error, "")
        self.assertEqual(answers, ["C"])
        self.assertTrue(metadata["fallbackUsed"])
        self.assertEqual(metadata["provider"], "siliconflow")
        self.assertEqual(metadata["model"], "Qwen/Qwen3.5-27B")
        self.assertEqual(metadata["targetSubmitDelaySeconds"], 40.0)


if __name__ == "__main__":
    unittest.main()
