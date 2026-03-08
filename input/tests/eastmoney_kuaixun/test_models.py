from eastmoney_kuaixun.models import (
    ArticleDetail,
    CollectorState,
    FastNewsItem,
    PendingArticleBatchItem,
)


def test_fast_news_item_seen_key_prefers_code_and_real_sort() -> None:
    item = FastNewsItem(
        code="123456789",
        title="title",
        summary="summary",
        show_time="2026-03-08 11:31:00",
        real_sort="1772939953000",
        url="https://finance.eastmoney.com/a/123456789.html",
    )
    assert item.seen_key == "123456789:1772939953000"


def test_fast_news_item_seen_key_falls_back_to_show_time_and_title() -> None:
    item = FastNewsItem(
        code="",
        title="title",
        summary="summary",
        show_time="2026-03-08 11:31:00",
        real_sort="1772939953000",
        url="",
    )
    assert item.seen_key == "2026-03-08 11:31:00:title"


def test_collector_state_tracks_recent_ids() -> None:
    state = CollectorState(last_real_sort="10", recent_ids=["a", "b"])
    assert state.last_real_sort == "10"
    assert state.recent_ids == ["a", "b"]


def test_article_detail_to_pending_item_preserves_article_fields() -> None:
    detail = ArticleDetail(
        code="202603083665282988",
        title="标题",
        summary="摘要",
        show_time="2026-03-08 08:37:03",
        real_sort="100",
        url="https://finance.eastmoney.com/a/202603083665282988.html",
        author="作者",
        source="来源",
        content_text="正文",
    )
    item = detail.to_pending_item()
    assert item.code == "202603083665282988"
    assert item.content_text == "正文"


def test_collector_state_tracks_article_batch_progress() -> None:
    state = CollectorState(
        last_real_sort="101",
        recent_ids=["a"],
        article_batch_index=2,
        article_pending_items=[
            PendingArticleBatchItem(
                code="1",
                title="t",
                summary="s",
                show_time="2026-03-08 08:37:03",
                real_sort="101",
                url="u",
                author="a",
                source="src",
                content_text="body",
            )
        ],
    )
    assert state.article_batch_index == 2
    assert len(state.article_pending_items) == 1
