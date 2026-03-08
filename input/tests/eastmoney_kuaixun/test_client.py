from pathlib import Path

from eastmoney_kuaixun.client import (
    build_count_url,
    build_list_url,
    parse_detail_html,
    parse_count_payload,
    parse_list_payload,
)


def test_parse_count_payload_reads_increment_count() -> None:
    payload = {"data": {"count": 3}}
    assert parse_count_payload(payload) == 3


def test_parse_list_payload_returns_fast_news_items() -> None:
    payload = {
        "data": {
            "fastNewsList": [
                {
                    "code": "123",
                    "title": "title",
                    "summary": "summary",
                    "showTime": "2026-03-08 11:31:00",
                    "realSort": "100",
                }
            ]
        }
    }
    items = parse_list_payload(payload)
    assert len(items) == 1
    assert items[0].real_sort == "100"
    assert items[0].url.endswith("/123.html")


def test_parse_list_payload_skips_dirty_items_without_real_sort() -> None:
    payload = {
        "data": {
            "fastNewsList": [
                {
                    "code": "123",
                    "title": "title",
                    "summary": "summary",
                    "showTime": "2026-03-08 11:31:00",
                }
            ]
        }
    }
    assert parse_list_payload(payload) == []


def test_build_urls_include_required_boundary_params() -> None:
    assert "sortStart=10" in build_count_url("101", "10")
    assert "sortEnd=20" in build_list_url("101", "20", 5)


def test_parse_detail_html_extracts_content_author_and_source() -> None:
    html = Path("tests/fixtures/detail_page.html").read_text(encoding="utf-8")
    detail = parse_detail_html(
        html=html,
        code="202603083665282988",
        title="AI终于学会自己干活了！大厂纷纷布局OpenClaw",
        summary="摘要",
        show_time="2026-03-08 08:37:03",
        real_sort="100",
        url="https://finance.eastmoney.com/a/202603083665282988.html",
    )
    assert "养虾人" in detail.content_text
    assert detail.author == "宋亚芬"
    assert detail.source == "中新经纬"


def test_parse_detail_html_raises_when_content_body_missing() -> None:
    html = "<html><body><div>empty</div></body></html>"
    try:
        parse_detail_html(
            html=html,
            code="1",
            title="t",
            summary="s",
            show_time="2026-03-08 08:37:03",
            real_sort="100",
            url="u",
        )
    except ValueError as exc:
        assert "ContentBody" in str(exc)
    else:
        raise AssertionError("expected ValueError")
