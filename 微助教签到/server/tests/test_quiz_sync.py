import time
import unittest
from unittest.mock import AsyncMock, patch

from routers.quiz import (
    QUESTION_DETAIL_CACHE,
    _resolve_master_contents,
    _sync_choice_to_sub,
)


class FakeSession:
    def __init__(self, detail):
        self.detail = detail
        self.submissions = []

    async def get_question_detail(self, question_id):
        return self.detail

    async def submit_answer(self, course_id, question_id, answer, files=None, audio=None,
                            question_type=None):
        self.submissions.append({
            "course_id": course_id,
            "question_id": question_id,
            "answer": answer,
            "files": files,
            "audio": audio,
            "question_type": question_type,
        })
        return {"ok": True}


class QuizSemanticSyncTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self):
        QUESTION_DETAIL_CACHE.clear()

    async def test_resolves_master_content_from_server_snapshot_by_rank(self):
        QUESTION_DETAIL_CACHE[(10, 20)] = {
            "timestamp": time.time(),
            "data": {
                "answerContent": [
                    {"rank": 2, "content": "<p>正确内容</p>"},
                    {"rank": 0, "content": "<p>其他内容</p>"},
                ]
            },
        }

        contents = await _resolve_master_contents(
            "MASTER", 10, 20, [2], ["<p>客户端错误快照</p>"],
        )

        self.assertEqual(contents, ["<p>正确内容</p>"])

    async def test_sub_account_submission_uses_semantically_matched_shuffled_rank(self):
        session = FakeSession({
            "answerContent": [
                {"rank": "9", "content": "<p>其他选项</p>"},
                {"rank": "6", "content": "<div>垂直 纸面朝内</div>"},
            ]
        })

        with (
            patch("routers.quiz.get_tm_session", return_value=session),
            patch("routers.quiz.log_answer", new=AsyncMock()) as log_answer,
        ):
            result = await _sync_choice_to_sub(
                "SUB", 10, 20, 1,
                ["<p>垂直&nbsp;纸面朝内</p>"], [0], [], [],
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["matched_ranks"], [6])
        self.assertEqual(session.submissions[0]["answer"], [6])
        self.assertEqual(session.submissions[0]["question_type"], 1)
        log_answer.assert_awaited_once()

    async def test_sub_account_is_not_submitted_when_semantic_match_fails(self):
        session = FakeSession({
            "answerContent": [{"rank": 0, "content": "<p>完全不同</p>"}]
        })

        with (
            patch("routers.quiz.get_tm_session", return_value=session),
            patch("routers.quiz.log_answer", new=AsyncMock()) as log_answer,
        ):
            result = await _sync_choice_to_sub(
                "SUB", 10, 20, 1, ["<p>主账号答案</p>"], [0], [], [],
            )

        self.assertFalse(result["success"])
        self.assertIn("选项匹配失败", result["message"])
        self.assertEqual(session.submissions, [])
        log_answer.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
