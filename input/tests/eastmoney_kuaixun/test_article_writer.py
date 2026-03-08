from pathlib import Path

from eastmoney_kuaixun.article_writer import (
    build_article_batch_dir_name,
    write_article_batch,
)
from eastmoney_kuaixun.models import PendingArticleBatchItem


def test_build_article_batch_dir_name_uses_anchor_time_and_index() -> None:
    item = PendingArticleBatchItem(
        code="202603083665282988",
        title="标题",
        summary="摘要",
        show_time="2026-03-08 08:37:03",
        real_sort="100",
        url="u",
        author="a",
        source="src",
        content_text="body",
    )
    assert build_article_batch_dir_name(item, 1) == "20260308-083703_0001"


def test_write_article_batch_writes_five_article_files(tmp_path: Path) -> None:
    items: list[PendingArticleBatchItem] = []
    for index in range(5):
        items.append(
            PendingArticleBatchItem(
                code=str(index + 1),
                title=f"title-{index + 1}",
                summary="summary",
                show_time=f"2026-03-08 08:37:0{index + 1}",
                real_sort=str(100 + index),
                url=f"https://example.com/{index + 1}",
                author="a",
                source="src",
                content_text=f"body-{index + 1}",
            )
        )
    output_dir, written_files = write_article_batch(tmp_path, items, batch_index=1)
    assert output_dir.name == "20260308-083701_0001"
    assert len(list(output_dir.glob("*.md"))) == 5
    assert len(written_files) == 5
    first_file = output_dir / "01-1.md"
    assert first_file.exists()
    assert "## 正文" in first_file.read_text(encoding="utf-8")
