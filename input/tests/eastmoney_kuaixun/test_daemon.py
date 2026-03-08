import random
from pathlib import Path

from eastmoney_kuaixun.config import load_settings
from eastmoney_kuaixun.daemon import (
    compute_next_interval,
    filter_new_items,
    run_collection_cycle,
)
from eastmoney_kuaixun.models import ArticleDetail, CollectorState, FastNewsItem


class StubClient:
    def __init__(self, count: int, items: list[FastNewsItem]) -> None:
        self.count = count
        self.items = items
        self.list_calls = 0

    def fetch_increment_count(self, sort_start: str) -> int:
        return self.count

    def fetch_latest_items(self, sort_end: str) -> list[FastNewsItem]:
        self.list_calls += 1
        return self.items


class DetailStubClient(StubClient):
    def __init__(
        self,
        count: int,
        items: list[FastNewsItem],
        details: dict[str, ArticleDetail],
        failing_codes: set[str] | None = None,
    ) -> None:
        super().__init__(count=count, items=items)
        self.details = details
        self.failing_codes = failing_codes or set()

    def fetch_article_detail(self, item: FastNewsItem) -> ArticleDetail:
        if item.code in self.failing_codes:
            raise ValueError(f"detail failed for {item.code}")
        return self.details[item.code]


def make_fast_news_item(code: str, show_time: str, real_sort: str) -> FastNewsItem:
    return FastNewsItem(
        code=code,
        title=f"title-{code}",
        summary=f"summary-{code}",
        show_time=show_time,
        real_sort=real_sort,
        url=f"https://finance.eastmoney.com/a/{code}.html",
    )


def make_article_detail(code: str, show_time: str, real_sort: str) -> ArticleDetail:
    item = make_fast_news_item(code, show_time, real_sort)
    return ArticleDetail(
        code=item.code,
        title=item.title,
        summary=item.summary,
        show_time=item.show_time,
        real_sort=item.real_sort,
        url=item.url,
        author="author",
        source="source",
        content_text=f"body-{code}",
    )


def test_filter_new_items_skips_old_and_duplicate_items() -> None:
    items = [
        FastNewsItem(code="a", title="t1", summary="s1", show_time="2026-03-08 11:31:00", real_sort="100", url="u1"),
        FastNewsItem(code="b", title="t2", summary="s2", show_time="2026-03-08 11:32:00", real_sort="101", url="u2"),
    ]
    result = filter_new_items(items, last_real_sort="100", recent_ids={"b:101"})
    assert result == []


def test_run_collection_cycle_skips_list_when_count_is_zero(tmp_path: Path) -> None:
    settings = load_settings(tmp_path)
    client = StubClient(count=0, items=[])
    result = run_collection_cycle(client, settings, CollectorState(), empty_rounds=0, failure_count=0, rng=random.Random(1))
    assert result.written == 0
    assert client.list_calls == 1


def test_run_collection_cycle_still_uses_list_when_count_is_zero_but_items_exist(
    tmp_path: Path,
) -> None:
    settings = load_settings(tmp_path)
    item = FastNewsItem(
        code="123",
        title="title",
        summary="summary",
        show_time="2026-03-08 11:31:00",
        real_sort="100",
        url="https://finance.eastmoney.com/a/123.html",
    )
    client = DetailStubClient(
        count=0,
        items=[item],
        details={item.code: make_article_detail(item.code, item.show_time, item.real_sort)},
    )
    result = run_collection_cycle(
        client,
        settings,
        CollectorState(last_real_sort="99", recent_ids=[]),
        empty_rounds=0,
        failure_count=0,
        rng=random.Random(1),
    )
    assert client.list_calls == 1
    assert result.written == 1
    assert result.state.last_real_sort == "100"


def test_compute_next_interval_uses_backoff_for_failures(tmp_path: Path) -> None:
    settings = load_settings(tmp_path)
    assert compute_next_interval(settings, empty_rounds=0, failure_count=2, rng=random.Random(1)) == 300


def test_run_collection_cycle_writes_articles_immediately_before_batch_reaches_five(
    tmp_path: Path,
) -> None:
    settings = load_settings(tmp_path)
    items = [
        make_fast_news_item("1", "2026-03-08 08:37:01", "100"),
        make_fast_news_item("2", "2026-03-08 08:37:02", "101"),
    ]
    client = DetailStubClient(
        count=2,
        items=items,
        details={item.code: make_article_detail(item.code, item.show_time, item.real_sort) for item in items},
    )
    result = run_collection_cycle(
        client,
        settings,
        CollectorState(),
        empty_rounds=0,
        failure_count=0,
        rng=random.Random(1),
    )
    assert result.written == 2
    assert result.state.article_batch_index == 1
    assert result.state.current_article_batch_day == "2026-03-08"
    assert result.state.current_article_batch_dir_name == "20260308-083701_0001"
    assert result.state.current_article_batch_item_count == 2
    batch_dir = settings.articles_dir / "2026-03-08" / "20260308-083701_0001"
    assert batch_dir.exists()
    assert len(list(batch_dir.glob("*.md"))) == 2
    raw_markdown = (settings.raw_dir / "eastmoney-yw-2026-03.md").read_text(encoding="utf-8")
    assert "articles/2026-03-08/20260308-083701_0001/01-1.md" in raw_markdown
    assert "articles/2026-03-08/20260308-083701_0001/02-2.md" in raw_markdown


def test_run_collection_cycle_flushes_article_batch_when_pending_reaches_five(
    tmp_path: Path,
) -> None:
    settings = load_settings(tmp_path)
    items = [
        make_fast_news_item("3", "2026-03-08 08:37:03", "102"),
        make_fast_news_item("4", "2026-03-08 08:37:04", "103"),
        make_fast_news_item("5", "2026-03-08 08:37:05", "104"),
    ]
    pending_items = [
        make_article_detail("1", "2026-03-08 08:37:01", "100").to_pending_item(),
        make_article_detail("2", "2026-03-08 08:37:02", "101").to_pending_item(),
    ]
    batch_dir = settings.articles_dir / "2026-03-08" / "20260308-083701_0001"
    batch_dir.mkdir(parents=True, exist_ok=True)
    for position, pending_item in enumerate(pending_items, start=1):
        (batch_dir / f"{position:02d}-{pending_item.code}.md").write_text(
            "existing",
            encoding="utf-8",
        )
    client = DetailStubClient(
        count=3,
        items=items,
        details={item.code: make_article_detail(item.code, item.show_time, item.real_sort) for item in items},
    )
    result = run_collection_cycle(
        client,
        settings,
        CollectorState(
            last_real_sort="101",
            recent_ids=["1:100", "2:101"],
            article_batch_index=1,
            article_pending_items=pending_items,
            current_article_batch_day="2026-03-08",
            current_article_batch_dir_name="20260308-083701_0001",
            current_article_batch_item_count=2,
        ),
        empty_rounds=0,
        failure_count=0,
        rng=random.Random(1),
    )
    assert result.written == 3
    assert result.state.article_batch_index == 1
    assert result.state.current_article_batch_item_count == 5
    assert batch_dir.exists()
    assert len(list(batch_dir.glob("*.md"))) == 5
    raw_markdown = (settings.raw_dir / "eastmoney-yw-2026-03.md").read_text(encoding="utf-8")
    assert "- article_file:" in raw_markdown
    assert "articles/2026-03-08/20260308-083701_0001/03-3.md" in raw_markdown


def test_run_collection_cycle_starts_new_batch_after_previous_batch_is_full(
    tmp_path: Path,
) -> None:
    settings = load_settings(tmp_path)
    item = make_fast_news_item("6", "2026-03-08 09:00:00", "105")
    client = DetailStubClient(
        count=1,
        items=[item],
        details={item.code: make_article_detail(item.code, item.show_time, item.real_sort)},
    )
    result = run_collection_cycle(
        client,
        settings,
        CollectorState(
            last_real_sort="104",
            recent_ids=["1:100", "2:101", "3:102", "4:103", "5:104"],
            article_batch_index=1,
            current_article_batch_day="2026-03-08",
            current_article_batch_dir_name="20260308-083701_0001",
            current_article_batch_item_count=5,
        ),
        empty_rounds=0,
        failure_count=0,
        rng=random.Random(1),
    )
    assert result.state.article_batch_index == 2
    assert result.state.current_article_batch_dir_name == "20260308-090000_0002"
    assert result.state.current_article_batch_item_count == 1
    batch_dir = settings.articles_dir / "2026-03-08" / "20260308-090000_0002"
    assert batch_dir.exists()
    assert (batch_dir / "01-6.md").exists()


def test_run_collection_cycle_starts_new_batch_when_news_day_changes(
    tmp_path: Path,
) -> None:
    settings = load_settings(tmp_path)
    item = make_fast_news_item("7", "2026-03-08 08:37:03", "106")
    client = DetailStubClient(
        count=1,
        items=[item],
        details={item.code: make_article_detail(item.code, item.show_time, item.real_sort)},
    )
    result = run_collection_cycle(
        client,
        settings,
        CollectorState(
            last_real_sort="105",
            recent_ids=["6:105"],
            article_batch_index=8,
            current_article_batch_day="2026-03-07",
            current_article_batch_dir_name="20260307-163747_0008",
            current_article_batch_item_count=4,
        ),
        empty_rounds=0,
        failure_count=0,
        rng=random.Random(1),
    )
    assert result.state.article_batch_index == 9
    assert result.state.current_article_batch_day == "2026-03-08"
    assert result.state.current_article_batch_dir_name == "20260308-083703_0009"
    assert result.state.current_article_batch_item_count == 1
    batch_dir = settings.articles_dir / "2026-03-08" / "20260308-083703_0009"
    assert batch_dir.exists()
    assert (batch_dir / "01-7.md").exists()


def test_run_collection_cycle_raises_when_article_detail_fetch_fails(tmp_path: Path) -> None:
    settings = load_settings(tmp_path)
    items = [make_fast_news_item("1", "2026-03-08 08:37:01", "100")]
    client = DetailStubClient(
        count=1,
        items=items,
        details={},
        failing_codes={"1"},
    )
    try:
        run_collection_cycle(
            client,
            settings,
            CollectorState(),
            empty_rounds=0,
            failure_count=0,
            rng=random.Random(1),
        )
    except ValueError as exc:
        assert "detail failed for 1" in str(exc)
    else:
        raise AssertionError("expected detail fetch failure")
