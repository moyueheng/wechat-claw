from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json
import re
import uuid

from .config import EASTMONEY_YW_COLUMN, Settings
from .models import ArticleDetail, FastNewsItem

API_BASE_URL = "https://np-listapi.eastmoney.com/comm/web"
DETAIL_BASE_URL = "https://finance.eastmoney.com/a"

CONTENT_BODY_PATTERN = re.compile(
    r'<div class="txtinfos" id="ContentBody"[^>]*>(?P<body>.*?)</div>',
    re.DOTALL,
)
AUTHOR_PATTERN = re.compile(
    r"作者：\s*(?P<author>[^<]+)</div>",
    re.DOTALL,
)
SOURCE_PATTERN = re.compile(
    r"来源：\s*(?P<source>[^<]+)</div>",
    re.DOTALL,
)
TRAILING_SOURCE_PATTERN = re.compile(
    r"文章来源：\s*(?P<source>[^<]+)</span>",
    re.DOTALL,
)
DISALLOWED_TEXT_SNIPPETS = (
    "文章来源：",
    "责任编辑：",
    "郑重声明：",
)


class ContentBodyTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._paragraphs: list[str] = []
        self._current_parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = dict(attrs)
        if tag in {"script", "style"}:
            self._skip_depth += 1
            return
        if tag == "img":
            return
        if tag == "p":
            self._flush_current(force=False)
        if tag == "br":
            self._current_parts.append("\n")
        if tag in {"strong", "a", "span"} and attrs_map.get("class") == "em_media":
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._skip_depth > 0:
            self._skip_depth -= 1
            return
        if tag == "p":
            self._flush_current(force=True)
        if tag in {"strong", "a", "span"} and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        cleaned = data.replace("\xa0", " ").strip()
        if cleaned:
            self._current_parts.append(cleaned)

    def get_text(self) -> str:
        self._flush_current(force=True)
        filtered = [
            paragraph
            for paragraph in self._paragraphs
            if paragraph and not any(snippet in paragraph for snippet in DISALLOWED_TEXT_SNIPPETS)
        ]
        return "\n\n".join(filtered)

    def _flush_current(self, force: bool) -> None:
        if not self._current_parts:
            return
        merged = "".join(self._current_parts).strip()
        self._current_parts = []
        if merged or force:
            normalized = re.sub(r"\n{2,}", "\n", merged).strip()
            if normalized:
                self._paragraphs.append(normalized)


def build_count_url(column: str, sort_start: str) -> str:
    query = urlencode(
        {
            "client": "web",
            "biz": "web_724",
            "fastColumn": column,
            "sortStart": sort_start,
            "req_trace": uuid.uuid4().hex,
        }
    )
    return f"{API_BASE_URL}/getFastNewsCount?{query}"


def build_list_url(column: str, sort_end: str, page_size: int) -> str:
    query = urlencode(
        {
            "client": "web",
            "biz": "web_724",
            "fastColumn": column,
            "sortEnd": sort_end,
            "pageSize": str(page_size),
            "req_trace": uuid.uuid4().hex,
        }
    )
    return f"{API_BASE_URL}/getFastNewsList?{query}"


def parse_count_payload(payload: dict[str, Any]) -> int:
    data = payload.get("data") or {}
    return int(data.get("count", 0) or 0)


def build_detail_url(code: str) -> str:
    return f"{DETAIL_BASE_URL}/{code}.html" if code else ""


def parse_list_payload(payload: dict[str, Any]) -> list[FastNewsItem]:
    data = payload.get("data") or {}
    raw_items = data.get("fastNewsList") or []
    items: list[FastNewsItem] = []
    for raw_item in raw_items:
        real_sort = str(raw_item.get("realSort", "") or "")
        if not real_sort:
            continue
        code = str(raw_item.get("code", "") or "")
        items.append(
            FastNewsItem(
                code=code,
                title=str(raw_item.get("title", "") or ""),
                summary=str(raw_item.get("summary", "") or ""),
                show_time=str(raw_item.get("showTime", "") or ""),
                real_sort=real_sort,
                url=str(raw_item.get("url", "") or build_detail_url(code)),
            )
        )
    return items


def _extract_meta_value(pattern: re.Pattern[str], html: str) -> str:
    match = pattern.search(html)
    if not match:
        return ""
    return _strip_tags(match.group(1 if match.lastindex else "source"))


def _strip_tags(value: str) -> str:
    text = re.sub(r"<[^>]+>", "", value)
    return unescape(" ".join(text.split()))


def parse_detail_html(
    html: str,
    code: str,
    title: str,
    summary: str,
    show_time: str,
    real_sort: str,
    url: str,
) -> ArticleDetail:
    body_match = CONTENT_BODY_PATTERN.search(html)
    if not body_match:
        raise ValueError("ContentBody not found")
    extractor = ContentBodyTextExtractor()
    extractor.feed(body_match.group("body"))
    content_text = extractor.get_text()
    if not content_text:
        raise ValueError("ContentBody is empty")
    author = _extract_meta_value(AUTHOR_PATTERN, html)
    source = _extract_meta_value(SOURCE_PATTERN, html) or _extract_meta_value(
        TRAILING_SOURCE_PATTERN, html
    )
    return ArticleDetail(
        code=code,
        title=title,
        summary=summary,
        show_time=show_time,
        real_sort=real_sort,
        url=url,
        author=author,
        source=source,
        content_text=content_text,
    )


@dataclass
class EastMoneyClient:
    settings: Settings

    def _get_json(self, url: str) -> dict[str, Any]:
        request = Request(
            url,
            headers={
                "User-Agent": self.settings.user_agent,
                "Referer": "https://kuaixun.eastmoney.com/yw.html",
                "Accept": "application/json,text/plain,*/*",
            },
        )
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def fetch_increment_count(self, sort_start: str) -> int:
        return parse_count_payload(
            self._get_json(build_count_url(EASTMONEY_YW_COLUMN, sort_start))
        )

    def fetch_latest_items(self, sort_end: str) -> list[FastNewsItem]:
        return parse_list_payload(
            self._get_json(
                build_list_url(EASTMONEY_YW_COLUMN, sort_end, self.settings.page_size)
            )
        )

    def fetch_article_detail(self, item: FastNewsItem) -> ArticleDetail:
        if not item.url:
            raise ValueError("article url is required")
        request = Request(
            item.url,
            headers={
                "User-Agent": self.settings.user_agent,
                "Referer": "https://kuaixun.eastmoney.com/yw.html",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        with urlopen(request, timeout=20) as response:
            html = response.read().decode("utf-8", errors="ignore")
        return parse_detail_html(
            html=html,
            code=item.code,
            title=item.title,
            summary=item.summary,
            show_time=item.show_time,
            real_sort=item.real_sort,
            url=item.url,
        )
