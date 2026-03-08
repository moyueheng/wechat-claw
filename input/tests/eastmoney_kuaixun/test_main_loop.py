from pathlib import Path

from eastmoney_kuaixun.config import load_settings
from eastmoney_kuaixun.daemon import run_main_loop
from eastmoney_kuaixun.models import ArticleDetail, CollectorState, FastNewsItem
from eastmoney_kuaixun.state import load_state, save_state


class SuccessClient:
    def __init__(self) -> None:
        self.count_calls = 0

    def fetch_increment_count(self, sort_start: str) -> int:
        self.count_calls += 1
        return 1

    def fetch_latest_items(self, sort_end: str) -> list[FastNewsItem]:
        return [
            FastNewsItem(
                code="123",
                title="title",
                summary="summary",
                show_time="2026-03-08 11:31:00",
                real_sort="100",
                url="https://finance.eastmoney.com/a/123.html",
            )
        ]

    def fetch_article_detail(self, item: FastNewsItem) -> ArticleDetail:
        return ArticleDetail(
            code=item.code,
            title=item.title,
            summary=item.summary,
            show_time=item.show_time,
            real_sort=item.real_sort,
            url=item.url,
            author="author",
            source="source",
            content_text="body",
        )


class FailingClient:
    def fetch_increment_count(self, sort_start: str) -> int:
        raise RuntimeError("boom")


def test_run_main_loop_saves_state_after_success(tmp_path: Path) -> None:
    settings = load_settings(tmp_path)
    exit_code = run_main_loop(settings=settings, client=SuccessClient(), once=True)
    assert exit_code == 0
    state = load_state(settings.state_file)
    assert state.last_real_sort == "100"
    assert state.article_batch_index == 1
    assert state.current_article_batch_item_count == 1


def test_run_main_loop_returns_error_on_once_failure(tmp_path: Path) -> None:
    settings = load_settings(tmp_path)
    exit_code = run_main_loop(settings=settings, client=FailingClient(), once=True)
    assert exit_code == 1


def test_run_main_loop_force_refresh_ignores_existing_state(tmp_path: Path) -> None:
    settings = load_settings(tmp_path)
    save_state(
        settings.state_file,
        CollectorState(
            last_real_sort="100",
            recent_ids=["123:100"],
            article_batch_index=0,
            article_pending_items=[],
        ),
    )
    exit_code = run_main_loop(
        settings=settings,
        client=SuccessClient(),
        once=True,
        force_refresh=True,
    )
    assert exit_code == 0
    state = load_state(settings.state_file)
    assert state.last_real_sort == "100"
    assert state.article_batch_index == 1
    assert state.current_article_batch_item_count == 1
