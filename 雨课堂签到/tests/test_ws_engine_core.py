import os
import sys
import tempfile
import unittest
import json
import asyncio
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("YKT_DATA_DIR", tempfile.mkdtemp(prefix="ykt-ws-tests-"))
os.environ.setdefault("PUSH_PLUS_TOKEN", "")

from safe_json_store import ACCOUNTS_STORE  # noqa: E402
from ykt_ws_engine import LessonRuntime, YktWsEngine, first_defined  # noqa: E402


class WsEngineCoreTests(unittest.TestCase):
    def setUp(self):
        ACCOUNTS_STORE.write(
            [
                {
                    "phone": "1",
                    "uid": 1,
                    "cookie": "a=1",
                    "lessonToken": "token-1",
                    "lessonId": "100",
                    "group_key": "group-a",
                    "ai_mode": True,
                    "expired": False,
                },
                {
                    "phone": "2",
                    "uid": 2,
                    "cookie": "a=2",
                    "lessonToken": "token-2",
                    "lessonId": "200",
                    "group_key": "group-a",
                    "ai_mode": True,
                    "expired": False,
                },
                {
                    "phone": "3",
                    "uid": 3,
                    "cookie": "a=3",
                    "lessonToken": "token-3",
                    "lessonId": "100",
                    "group_key": "group-b",
                    "ai_mode": True,
                    "expired": False,
                },
            ]
        )
        self.engine = YktWsEngine()

    def test_zero_problem_type_is_preserved(self):
        self.assertEqual(first_defined(0, 1), 0)
        extracted = self.engine.extract_content({}, {"problemType": 0, "options": ["a"]})
        self.assertEqual(extracted["problemType"], 0)

    def test_probe_is_scoped_by_group_and_lesson(self):
        runtime = LessonRuntime("group-a", "200", 1)
        probe = self.engine.get_probe_account(runtime)
        self.assertEqual(probe["uid"], 2)
        self.assertEqual([item["uid"] for item in self.engine.get_ready_accounts(runtime)], [2])

    def test_lesson_cleanup_is_scoped(self):
        self.engine.clear_lesson_tokens("group-a", "100")
        rows = {item["phone"]: item for item in ACCOUNTS_STORE.read()}
        self.assertEqual(rows["1"]["lessonToken"], "")
        self.assertGreater(rows["1"]["lessonCredentialUpdatedAt"], 0)
        self.assertEqual(rows["2"]["lessonToken"], "token-2")
        self.assertEqual(rows["3"]["lessonToken"], "token-3")

    def test_nested_presentation_and_shape_cover_are_extracted(self):
        payload = {
            "data": {
                "data": {
                    "presentationData": {
                        "slides": [
                            {
                                "id": "slide-1",
                                "index": 0,
                                "shapes": [{"children": [{"URL": "/media/question.png"}]}],
                            }
                        ],
                        "problems": [
                            {
                                "problemId": "9007199254740993",
                                "problemType": 0,
                                "slideIndex": 0,
                                "body": "请选择",
                                "options": [{"key": "A", "value": "甲"}],
                            }
                        ],
                    }
                }
            }
        }
        extracted = self.engine.extract_problem(payload, "9007199254740993")
        self.assertEqual(extracted["problemType"], 0)
        self.assertEqual(extracted["options"][0]["key"], "A")
        self.assertTrue(extracted["cover"].endswith("/media/question.png"))

    def test_presentation_state_fills_problem_context_and_end_alias_cleans_up(self):
        runtime = LessonRuntime("group-a", "100", 1)
        self.engine.runtimes[runtime.key] = runtime
        scheduled = []
        self.engine.schedule_problem = lambda rt, problem, raw: scheduled.append(problem)
        self.engine.notify = lambda title, content: None

        async def scenario():
            await self.engine.process_message(
                runtime,
                json.dumps(
                    {
                        "op": "hello",
                        "code": 0,
                        "lessonid": 100,
                        "data": {
                            "presentation_id": "pres-1",
                            "sid": "slide-2",
                            "si": 1,
                            "unlockedproblem": [
                                {"problemid": 77, "problemType": 0}
                            ],
                        },
                    }
                ),
            )
            await self.engine.process_message(
                runtime,
                json.dumps({"op": "finishlesson", "lessonid": 100}),
            )

        asyncio.run(scenario())
        self.assertEqual(scheduled[0]["pres"], "pres-1")
        self.assertEqual(scheduled[0]["sid"], "slide-2")
        self.assertEqual(scheduled[0]["si"], 1)
        self.assertTrue(runtime.stopped)
        rows = {item["phone"]: item for item in ACCOUNTS_STORE.read()}
        self.assertEqual(rows["1"]["lessonToken"], "")
        self.assertEqual(rows["2"]["lessonToken"], "token-2")

    def test_dynamic_websocket_url_only_accepts_official_host(self):
        self.assertEqual(
            self.engine.websocket_url_for(
                {"lessonContext": {"wssUrl": "wss://live.yuketang.cn/custom/"}}
            ),
            "wss://live.yuketang.cn/custom/",
        )
        self.assertNotEqual(
            self.engine.websocket_url_for(
                {"lessonContext": {"wssUrl": "wss://evil.example/wsapp/"}}
            ),
            "wss://evil.example/wsapp/",
        )

    def test_submission_window_prefers_35_seconds_and_caps_at_60(self):
        sent_at = 1_800_000_000_000
        timing = self.engine._submission_timing_from(
            {"sendTime": sent_at, "limit": 120},
            {},
            sent_at,
        )
        self.assertEqual(timing["started_at_ms"], sent_at)
        self.assertEqual(timing["submit_not_before_ms"], sent_at + 35_000)
        self.assertEqual(timing["thinking_cutoff_ms"], sent_at + 25_000)
        self.assertEqual(timing["hard_deadline_ms"], sent_at + 60_000)
        self.assertEqual(timing["analysis_deadline_ms"], sent_at + 54_000)

    def test_short_teacher_deadline_overrides_preferred_delay(self):
        sent_at = 1_800_000_000_000
        timing = self.engine._submission_timing_from(
            {"sendTime": sent_at, "limit": 15},
            {},
            sent_at,
        )
        self.assertLess(timing["hard_deadline_ms"], sent_at + 15_000)
        self.assertLess(timing["submit_not_before_ms"], sent_at + 35_000)


if __name__ == "__main__":
    unittest.main()
