from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .models import FastNewsItem

SOURCE_URL = "https://kuaixun.eastmoney.com/yw.html"


def get_monthly_markdown_path(output_dir: Path, show_time: str) -> Path:
    return output_dir / f"eastmoney-yw-{show_time[:7]}.md"


def render_file_header(start_time: str) -> str:
    return (
        "# 东方财富焦点快讯归档\n\n"
        f"- 来源页: {SOURCE_URL}\n"
        "- 栏目: 101 / 焦点\n"
        f"- 开始记录时间: {start_time} +08:00\n\n"
    )


def render_item(item: FastNewsItem, article_file_path: Path | None = None) -> str:
    time_part = item.show_time[11:16]
    url_line = item.url or ""
    article_file_line = ""
    if article_file_path is not None:
        article_file_line = f"- article_file: {article_file_path.as_posix()}\n"
    return (
        f"### {time_part}\n"
        f"{item.body_text}\n\n"
        f"- title: {item.title}\n"
        f"- code: {item.code}\n"
        f"- real_sort: {item.real_sort}\n"
        f"- url: {url_line}\n"
        f"{article_file_line}\n"
    )


def to_relative_article_file_path(markdown_path: Path, article_file_path: Path) -> Path:
    return Path(
        article_file_path.relative_to(markdown_path.parent.parent).as_posix()
        if article_file_path.is_absolute()
        and markdown_path.parent.parent in article_file_path.parents
        else article_file_path.as_posix()
    )


def append_items_to_markdown(
    output_dir: Path,
    items: list[FastNewsItem],
    article_file_paths: dict[str, Path] | None = None,
) -> Path:
    if not items:
        raise ValueError("items must not be empty")
    output_dir.mkdir(parents=True, exist_ok=True)
    resolved_article_file_paths = article_file_paths or {}
    grouped_by_month: dict[Path, list[FastNewsItem]] = defaultdict(list)
    for item in items:
        grouped_by_month[get_monthly_markdown_path(output_dir, item.show_time)].append(item)
    written_paths = sorted(grouped_by_month.keys())
    for path, month_items in grouped_by_month.items():
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        chunks: list[str] = []
        if not existing:
            chunks.append(render_file_header(month_items[0].show_time))
        seen_dates = {line[3:] for line in existing.splitlines() if line.startswith("## ")}
        by_date: dict[str, list[FastNewsItem]] = defaultdict(list)
        for item in month_items:
            by_date[item.show_time[:10]].append(item)
        for day in sorted(by_date.keys()):
            if day not in seen_dates:
                chunks.append(f"## {day}\n\n")
            for item in by_date[day]:
                chunks.append(
                    render_item(
                        item,
                        article_file_path=(
                            to_relative_article_file_path(
                                path,
                                resolved_article_file_paths[item.seen_key],
                            )
                            if item.seen_key in resolved_article_file_paths
                            else None
                        ),
                    )
                )
        with path.open("a", encoding="utf-8") as handle:
            handle.write("".join(chunks))
    return written_paths[-1]
