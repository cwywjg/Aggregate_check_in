"""
答案选项匹配引擎。

微助教会为不同账号打乱选项的展示顺序，因此同步时只按选项内容匹配，
绝不沿用主账号的 rank。
"""
from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit


_INVISIBLE_RE = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060\ufeff]")
_WHITESPACE_RE = re.compile(r"\s+")


class _OptionHTMLParser(HTMLParser):
    """提取可见文字和图片标识，忽略标签样式与属性顺序。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self.images: list[str] = []
        self.ignored_depth = 0

    def handle_data(self, data: str) -> None:
        if self.ignored_depth == 0:
            self.text_parts.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style"}:
            self.ignored_depth += 1
            return
        if self.ignored_depth:
            return
        if tag in {"br", "p", "div", "li", "tr"}:
            self.text_parts.append(" ")
        if tag != "img":
            return

        attr_map = {key.lower(): value or "" for key, value in attrs}
        # data-data 通常是原图地址；没有时依次使用 src、alt。
        raw = attr_map.get("data-data") or attr_map.get("src") or attr_map.get("alt")
        if raw:
            self.images.append(raw)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style"} and self.ignored_depth:
            self.ignored_depth -= 1


@dataclass(frozen=True)
class OptionSignature:
    text: str
    images: tuple[str, ...]


@dataclass
class MatchResult:
    ref: str
    nickname: str = ""
    matched: bool = False
    matched_ranks: list[int] = field(default_factory=list)
    success: bool = False
    message: str = ""


class AnswerMatcher:
    """确定性的选项语义匹配器；遇到歧义时终止该子账号提交。"""

    @staticmethod
    def _parse(content: object) -> tuple[str, list[str]]:
        parser = _OptionHTMLParser()
        try:
            parser.feed("" if content is None else str(content))
            parser.close()
        except Exception:
            # HTMLParser 对残缺 HTML 很宽容；这里仍保留纯文本降级路径。
            return html.unescape("" if content is None else str(content)), []
        return "".join(parser.text_parts), parser.images

    @staticmethod
    def strip_html(content: object) -> str:
        """提取纯文本，并统一实体、不可见字符和多余空白。"""
        text, _ = AnswerMatcher._parse(content)
        text = unicodedata.normalize("NFKC", html.unescape(text))
        text = _INVISIBLE_RE.sub("", text).replace("\xa0", " ")
        return _WHITESPACE_RE.sub(" ", text).strip()

    @staticmethod
    def normalize(content: object) -> str:
        """用于比较的文本指纹：纯文本、NFKC、无空白、大小写折叠。"""
        return _WHITESPACE_RE.sub("", AnswerMatcher.strip_html(content)).casefold()

    @staticmethod
    def _normalize_image(raw: str) -> str:
        """去掉临时查询参数，仅保留稳定的图片路径/文件名。"""
        value = html.unescape(raw).strip()
        try:
            parsed = urlsplit(value)
            path = unquote(parsed.path or value)
        except ValueError:
            path = value.split("?", 1)[0].split("#", 1)[0]
        path = unicodedata.normalize("NFKC", path).replace("\\", "/").casefold()
        return path.rstrip("/")

    @classmethod
    def signature(cls, content: object) -> OptionSignature:
        """生成同时覆盖文字题和图片题的稳定语义指纹。"""
        _, images = cls._parse(content)
        normalized_images = tuple(filter(None, (cls._normalize_image(i) for i in images)))
        return OptionSignature(text=cls.normalize(content), images=normalized_images)

    @staticmethod
    def _rank(option: dict) -> int:
        rank = option.get("rank")
        if isinstance(rank, bool):
            raise ValueError("选项 rank 格式异常")
        try:
            return int(rank)
        except (TypeError, ValueError) as exc:
            raise ValueError("选项 rank 格式异常") from exc

    def _unique_rank(self, candidates: list[dict], used_ranks: set[int]) -> int | None:
        ranks = {self._rank(option) for option in candidates} - used_ranks
        if not ranks:
            return None
        if len(ranks) > 1:
            raise ValueError("存在多个内容相同的选项，无法确定唯一答案")
        return ranks.pop()

    def match_single(
        self,
        master_content: object,
        sub_options: list[dict],
        used_ranks: set[int] | None = None,
    ) -> int | None:
        """将一个主账号选项匹配到子账号唯一的 rank。"""
        used_ranks = used_ranks or set()
        master_raw = "" if master_content is None else str(master_content)

        # Level 1：原始 HTML 完全一致。
        exact = [o for o in sub_options if str(o.get("content", "")) == master_raw]
        rank = self._unique_rank(exact, used_ranks)
        if rank is not None:
            return rank

        master_signature = self.signature(master_content)
        if not master_signature.text and not master_signature.images:
            return None

        # Level 2：文字+图片整体一致，避免同文字不同配图的选项被误配。
        if master_signature.text and master_signature.images:
            signature_matches = [
                option for option in sub_options
                if self.signature(option.get("content", "")) == master_signature
            ]
            rank = self._unique_rank(signature_matches, used_ranks)
            if rank is not None:
                return rank

        # Level 3：可见文本一致；适配标签、样式、实体和空白差异。
        if master_signature.text and not master_signature.images:
            text_matches = [
                option for option in sub_options
                if self.signature(option.get("content", "")).text == master_signature.text
            ]
            rank = self._unique_rank(text_matches, used_ranks)
            if rank is not None:
                return rank

        # Level 4：图片路径集合一致；用于没有可见文字的图片选项。
        if master_signature.images and not master_signature.text:
            image_matches = [
                option for option in sub_options
                if self.signature(option.get("content", "")).images == master_signature.images
            ]
            rank = self._unique_rank(image_matches, used_ranks)
            if rank is not None:
                return rank

        return None

    def match_choice(self, master_contents: list[object], sub_options: list[dict]) -> list[int]:
        """匹配单选/多选答案；任一选项缺失或歧义时不生成提交数据。"""
        if not master_contents:
            raise ValueError("主账号答案缺少选项内容")
        if not sub_options or not all(isinstance(option, dict) for option in sub_options):
            raise ValueError("子账号选项数据为空或格式异常")

        ranks: list[int] = []
        used_ranks: set[int] = set()
        for content in master_contents:
            rank = self.match_single(content, sub_options, used_ranks)
            if rank is None:
                preview = self.strip_html(content)[:50] or "[图片选项]"
                raise ValueError(f"未找到语义一致的选项: '{preview}'")
            ranks.append(rank)
            used_ranks.add(rank)
        return ranks

    def build_sub_answer(
        self,
        question_type: int,
        master_contents: list[object],
        master_answer: list,
        sub_options: list[dict],
    ) -> list:
        if question_type in (1, 2, 3):
            return self.match_choice(master_contents, sub_options)
        return master_answer


answer_matcher = AnswerMatcher()
