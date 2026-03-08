from pathlib import Path

from eastmoney_kuaixun.models import FastNewsItem
from eastmoney_kuaixun.writer import append_items_to_markdown, render_item


def test_append_items_creates_monthly_markdown(tmp_path: Path) -> None:
    item = FastNewsItem(
        code="123",
        title="title",
        summary="summary",
        show_time="2026-03-08 11:31:00",
        real_sort="100",
        url="https://finance.eastmoney.com/a/123.html",
    )
    output = append_items_to_markdown(tmp_path, [item])
    content = output.read_text(encoding="utf-8")
    assert output.name == "eastmoney-yw-2026-03.md"
    assert "## 2026-03-08" in content
    assert "### 11:31" in content
    assert "- real_sort: 100" in content


def test_append_items_reuses_existing_day_section(tmp_path: Path) -> None:
    item1 = FastNewsItem(
        code="123",
        title="title-1",
        summary="summary-1",
        show_time="2026-03-08 11:31:00",
        real_sort="100",
        url="u1",
    )
    item2 = FastNewsItem(
        code="124",
        title="title-2",
        summary="summary-2",
        show_time="2026-03-08 11:35:00",
        real_sort="101",
        url="u2",
    )
    output = append_items_to_markdown(tmp_path, [item1])
    output = append_items_to_markdown(tmp_path, [item2])
    content = output.read_text(encoding="utf-8")
    assert content.count("## 2026-03-08") == 1
    assert "summary-1" in content
    assert "summary-2" in content


def test_render_item_can_include_article_file_path() -> None:
    item = FastNewsItem(
        code="123",
        title="title",
        summary="summary",
        show_time="2026-03-08 11:31:00",
        real_sort="100",
        url="https://finance.eastmoney.com/a/123.html",
    )
    rendered = render_item(item, article_file_path=Path("data/articles/2026-03-08/20260308-113100_0001/01-123.md"))
    assert "- article_file:" in rendered
    assert "01-123.md" in rendered


def test_append_items_uses_relative_article_file_path(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    article_file = tmp_path / "articles" / "2026-03-08" / "20260308-113100_0001" / "01-123.md"
    article_file.parent.mkdir(parents=True, exist_ok=True)
    article_file.write_text("body", encoding="utf-8")
    item = FastNewsItem(
        code="123",
        title="title",
        summary="summary",
        show_time="2026-03-08 11:31:00",
        real_sort="100",
        url="https://finance.eastmoney.com/a/123.html",
    )
    output = append_items_to_markdown(raw_dir, [item], article_file_paths={"123:100": article_file})
    content = output.read_text(encoding="utf-8")
    assert "- article_file: articles/2026-03-08/20260308-113100_0001/01-123.md" in content
