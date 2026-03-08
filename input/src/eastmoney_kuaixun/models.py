from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FastNewsItem:
    code: str
    title: str
    summary: str
    show_time: str
    real_sort: str
    url: str

    @property
    def seen_key(self) -> str:
        if self.code:
            return f"{self.code}:{self.real_sort}"
        return f"{self.show_time}:{self.title}"

    @property
    def body_text(self) -> str:
        return self.summary or self.title


@dataclass(frozen=True)
class PendingArticleBatchItem:
    code: str
    title: str
    summary: str
    show_time: str
    real_sort: str
    url: str
    author: str
    source: str
    content_text: str

    @property
    def seen_key(self) -> str:
        if self.code:
            return f"{self.code}:{self.real_sort}"
        return f"{self.show_time}:{self.title}"


@dataclass(frozen=True)
class ArticleDetail:
    code: str
    title: str
    summary: str
    show_time: str
    real_sort: str
    url: str
    author: str
    source: str
    content_text: str

    def to_pending_item(self) -> PendingArticleBatchItem:
        return PendingArticleBatchItem(
            code=self.code,
            title=self.title,
            summary=self.summary,
            show_time=self.show_time,
            real_sort=self.real_sort,
            url=self.url,
            author=self.author,
            source=self.source,
            content_text=self.content_text,
        )


@dataclass(frozen=True)
class CollectorState:
    last_real_sort: str = ""
    recent_ids: list[str] = field(default_factory=list)
    article_batch_index: int = 0
    article_pending_items: list[PendingArticleBatchItem] = field(default_factory=list)
    current_article_batch_day: str = ""
    current_article_batch_dir_name: str = ""
    current_article_batch_item_count: int = 0
