from __future__ import annotations

from pathlib import Path

from .models import PendingArticleBatchItem


def build_article_day_dir(base_dir: Path, anchor_item: PendingArticleBatchItem) -> Path:
    return base_dir / anchor_item.show_time[:10]


def build_article_batch_dir_name(
    anchor_item: PendingArticleBatchItem, batch_index: int
) -> str:
    timestamp = anchor_item.show_time.replace("-", "").replace(":", "").replace(" ", "-")
    return f"{timestamp}_{batch_index:04d}"


def build_article_file_name(item: PendingArticleBatchItem, position: int) -> str:
    code_or_fallback = item.code or item.real_sort or f"item-{position:02d}"
    return f"{position:02d}-{code_or_fallback}.md"


def render_article_markdown(
    item: PendingArticleBatchItem, batch_dir_name: str, position: int
) -> str:
    return (
        f"# {item.title}\n\n"
        f"- show_time: {item.show_time}\n"
        f"- code: {item.code}\n"
        f"- url: {item.url}\n"
        f"- author: {item.author}\n"
        f"- source: {item.source}\n"
        f"- real_sort: {item.real_sort}\n"
        f"- batch: {batch_dir_name}\n"
        f"- position: {position:02d}\n\n"
        "## 正文\n\n"
        f"{item.content_text}\n"
    )


def write_article_batch(
    base_dir: Path, items: list[PendingArticleBatchItem], batch_index: int
) -> tuple[Path, dict[str, Path]]:
    if len(items) != 5:
        raise ValueError("article batch must contain exactly 5 items")
    anchor_item = items[0]
    batch_dir_name = build_article_batch_dir_name(anchor_item, batch_index)
    output_dir = build_article_day_dir(base_dir, anchor_item) / batch_dir_name
    output_dir.mkdir(parents=True, exist_ok=True)
    written_files: dict[str, Path] = {}
    for position, item in enumerate(items, start=1):
        file_path = output_dir / build_article_file_name(item, position)
        file_path.write_text(
            render_article_markdown(item, batch_dir_name, position),
            encoding="utf-8",
        )
        written_files[item.seen_key] = file_path
    return output_dir, written_files


def append_article_to_batch(
    base_dir: Path,
    item: PendingArticleBatchItem,
    batch_day: str,
    batch_dir_name: str,
    position: int,
) -> Path:
    output_dir = base_dir / batch_day / batch_dir_name
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / build_article_file_name(item, position)
    file_path.write_text(
        render_article_markdown(item, batch_dir_name, position),
        encoding="utf-8",
    )
    return file_path
