import unittest
from unittest.mock import AsyncMock, patch

from routers.quiz import process_question_detail


class QuizDetailProcessingTests(unittest.IsolatedAsyncioTestCase):
    async def test_remote_choice_answer_and_option_ranks_are_normalized(self):
        detail = {
            "id": "99",
            "type": "1",
            "status": "2",
            "isAnswered": "1",
            "answerContent": [
                {"rank": "2", "content": "B", "answer": False},
                {"rank": "0", "content": "A", "answer": True},
            ],
            "answer": [{"rank": "2"}],
        }

        with patch("routers.quiz.get_cached_answer", new=AsyncMock()) as cached:
            result = await process_question_detail(detail, 123)

        self.assertEqual(result["serverAnswer"], [2])
        self.assertEqual(result["answerContent"][0]["rank"], 2)
        self.assertEqual(result["courseId"], 123)
        self.assertEqual(result["isOpen"], 0)
        cached.assert_not_awaited()

    async def test_answer_content_correct_flags_are_not_mistaken_for_student_answer(self):
        detail = {
            "id": 9,
            "type": 2,
            "status": 1,
            "isAnswered": 1,
            "answerContent": [
                {"rank": "4", "content": "A", "answer": True},
                {"rank": 7, "content": "B", "answer": True},
            ],
        }

        cached_row = {"master_ranks": '[7]', "file_keys": "[]"}
        with patch("routers.quiz.get_cached_answer", new=AsyncMock(return_value=cached_row)):
            result = await process_question_detail(detail, 45)

        self.assertEqual(result["serverAnswer"], [7])
        self.assertEqual(result["serverAnswerSource"], "local_cache")
        self.assertEqual(result["isOpen"], 1)

    async def test_choice_cache_uses_route_course_id_and_normalizes_rank_types(self):
        cached_row = {
            "master_ranks": '["1", 3]',
            "plain_texts": '["A", "C"]',
            "file_keys": "[]",
        }
        cached = AsyncMock(return_value=cached_row)
        detail = {
            "id": 77,
            "type": 1,
            "status": 2,
            "isAnswered": 0,
            "answerContent": [],
        }

        with patch("routers.quiz.get_cached_answer", new=cached):
            result = await process_question_detail(detail, 456)

        cached.assert_awaited_once_with(456, 77)
        self.assertEqual(result["serverAnswer"], [1, 3])
        self.assertEqual(result["isAnswered"], 1)
        self.assertEqual(result["serverAnswerSource"], "local_cache")

    async def test_fill_cache_reads_submitted_answer_not_choice_plain_texts(self):
        cached_row = {
            "master_ranks": '["第一空", "第二空"]',
            "plain_texts": "[]",
            "file_keys": "[]",
        }
        detail = {"id": 88, "type": 4, "status": 2, "isAnswered": 0}

        with patch("routers.quiz.get_cached_answer", new=AsyncMock(return_value=cached_row)):
            result = await process_question_detail(detail, 12)

        self.assertEqual(result["serverAnswer"], ["第一空", "第二空"])

    async def test_remote_fill_objects_are_sorted_and_reduced_to_text(self):
        detail = {
            "id": 89,
            "type": 4,
            "status": 2,
            "isAnswered": 1,
            "answer": [
                {"rank": "1", "answer": "第二空", "isCorrect": 1},
                {"rank": 0, "answer": "第一空", "isCorrect": 1},
            ],
        }

        result = await process_question_detail(detail, 12)

        self.assertEqual(result["serverAnswer"], ["第一空", "第二空"])
        self.assertEqual(result["serverAnswerSource"], "remote")

    async def test_judgement_options_are_synthesized_like_official_client(self):
        detail = {"id": 90, "type": 3, "status": 1, "isAnswered": 0, "answerContent": []}

        with patch("routers.quiz.get_cached_answer", new=AsyncMock(return_value=None)):
            result = await process_question_detail(detail, 12)

        self.assertEqual(result["answerContent"], [
            {"rank": 0, "content": "是"},
            {"rank": 1, "content": "否"},
        ])

    async def test_subjective_remote_answer_keeps_text_and_attachments_separate(self):
        detail = {
            "id": 66,
            "type": 5,
            "status": 2,
            "isAnswered": 1,
            "answer": {"answer": ["正文"], "attaches": ["https://files.example/a.png"]},
        }

        result = await process_question_detail(detail, 3)

        self.assertEqual(result["serverAnswer"], ["正文"])
        self.assertEqual(result["serverFiles"], ["https://files.example/a.png"])


if __name__ == "__main__":
    unittest.main()
