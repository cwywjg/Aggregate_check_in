import unittest
from unittest.mock import AsyncMock

from services.teachermate import TeacherMateSession


class TeacherMateSubmissionTests(unittest.IsolatedAsyncioTestCase):
    async def test_multiselect_uses_official_index_object_shape(self):
        session = TeacherMateSession("TEST")
        session.api_post = AsyncMock(return_value={"ok": True})

        await session.submit_answer(
            12, 34, [2, "4", 2], question_type=2,
        )

        session.api_post.assert_awaited_once_with(
            "/v3/students/answer/question",
            {
                "courseId": 12,
                "questionId": 34,
                "answer": [{"index": 2}, {"index": 4}],
                "files": [],
                "audio": [],
            },
        )

    async def test_single_choice_accepts_rank_object_but_writes_index(self):
        session = TeacherMateSession("TEST")
        session.api_post = AsyncMock(return_value={"ok": True})

        await session.submit_answer(12, 35, [{"rank": "1"}], question_type=1)

        body = session.api_post.await_args.args[1]
        self.assertEqual(body["answer"], [{"index": 1}])

    async def test_fill_and_subjective_keep_their_native_shapes(self):
        session = TeacherMateSession("TEST")
        session.api_post = AsyncMock(return_value={"ok": True})

        await session.submit_answer(1, 2, ["甲", "乙"], question_type=4)
        fill_body = session.api_post.await_args.args[1]
        self.assertEqual(fill_body["answer"], ["甲", "乙"])

        await session.submit_answer(1, 3, ["主观正文"], question_type=5)
        subjective_body = session.api_post.await_args.args[1]
        self.assertEqual(subjective_body["answer"], "主观正文")


if __name__ == "__main__":
    unittest.main()
