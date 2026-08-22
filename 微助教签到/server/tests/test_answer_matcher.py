import unittest

from services.answer_matcher import AnswerMatcher


class AnswerMatcherTests(unittest.TestCase):
    def setUp(self):
        self.matcher = AnswerMatcher()

    def test_normalizes_html_entities_unicode_and_invisible_whitespace(self):
        master = "<style>.x{color:red}</style><p>垂直&nbsp;纸面\u200b朝内</p><script>ignored()</script>"
        sub_options = [
            {"rank": "3", "content": "<div>垂直 纸面朝内</div>"},
            {"rank": 1, "content": "<p>垂直纸面朝外</p>"},
        ]

        self.assertEqual(self.matcher.match_choice([master], sub_options), [3])
        self.assertEqual(self.matcher.strip_html(master), "垂直 纸面朝内")

    def test_matches_shuffled_multiselect_by_content_not_master_rank(self):
        master_contents = ["<p>Alpha</p>", "<p>Gamma</p>"]
        shuffled = [
            {"rank": 8, "content": "<span>Gamma</span>"},
            {"rank": 4, "content": "<p>Beta</p>"},
            {"rank": 6, "content": "<div>Alpha</div>"},
        ]

        self.assertEqual(
            self.matcher.build_sub_answer(2, master_contents, [0, 2], shuffled),
            [6, 8],
        )

    def test_matches_image_only_option_with_stable_path(self):
        master = '<p><img data-data="https://cdn-a.example/a/answer.png?token=old"></p>'
        sub_options = [
            {"rank": 2, "content": '<img src="https://cdn-b.example/a/other.png">'},
            {"rank": 7, "content": '<div><img src="https://cdn-b.example/a/answer.png?token=new"></div>'},
        ]

        self.assertEqual(self.matcher.match_choice([master], sub_options), [7])

    def test_text_and_image_must_match_as_one_signature(self):
        master = '<p>图 A<img src="https://a.example/fig/correct.png"></p>'
        sub_options = [
            {"rank": 1, "content": '<p>图 A<img src="https://b.example/fig/wrong.png"></p>'},
            {"rank": 5, "content": '<div>图 A<img src="https://b.example/fig/correct.png?x=1"></div>'},
        ]

        self.assertEqual(self.matcher.match_choice([master], sub_options), [5])

    def test_rejects_ambiguous_duplicate_content(self):
        duplicate_options = [
            {"rank": 0, "content": "<p>相同答案</p>"},
            {"rank": 1, "content": "<p>相同答案</p>"},
        ]

        with self.assertRaisesRegex(ValueError, "多个内容相同"):
            self.matcher.match_choice(["<p>相同答案</p>"], duplicate_options)

    def test_rejects_missing_semantic_match_instead_of_reusing_master_rank(self):
        with self.assertRaisesRegex(ValueError, "未找到语义一致"):
            self.matcher.build_sub_answer(
                1,
                ["<p>主账号答案</p>"],
                [3],
                [{"rank": 3, "content": "<p>另一个答案</p>"}],
            )

    def test_rejects_empty_master_content(self):
        with self.assertRaisesRegex(ValueError, "缺少选项内容"):
            self.matcher.match_choice([], [{"rank": 0, "content": "A"}])


if __name__ == "__main__":
    unittest.main()
