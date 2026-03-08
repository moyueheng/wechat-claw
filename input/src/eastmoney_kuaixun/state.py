from __future__ import annotations

from pathlib import Path
import json
import os
import tempfile

from .models import CollectorState, PendingArticleBatchItem


def trim_recent_ids(recent_ids: list[str], limit: int) -> list[str]:
    if limit <= 0:
        return []
    if len(recent_ids) <= limit:
        return recent_ids[:]
    return recent_ids[-limit:]


def load_state(path: Path) -> CollectorState:
    if not path.exists():
        return CollectorState()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return CollectorState(
        last_real_sort=str(payload.get("last_real_sort", "")),
        recent_ids=[str(item) for item in payload.get("recent_ids", [])],
        article_batch_index=int(payload.get("article_batch_index", 0) or 0),
        article_pending_items=[
            PendingArticleBatchItem(
                code=str(item.get("code", "")),
                title=str(item.get("title", "")),
                summary=str(item.get("summary", "")),
                show_time=str(item.get("show_time", "")),
                real_sort=str(item.get("real_sort", "")),
                url=str(item.get("url", "")),
                author=str(item.get("author", "")),
                source=str(item.get("source", "")),
                content_text=str(item.get("content_text", "")),
            )
            for item in payload.get("article_pending_items", [])
        ],
        current_article_batch_day=str(payload.get("current_article_batch_day", "")),
        current_article_batch_dir_name=str(
            payload.get("current_article_batch_dir_name", "")
        ),
        current_article_batch_item_count=int(
            payload.get("current_article_batch_item_count", 0) or 0
        ),
    )


def save_state(path: Path, state: CollectorState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "last_real_sort": state.last_real_sort,
        "recent_ids": state.recent_ids,
        "article_batch_index": state.article_batch_index,
        "article_pending_items": [
            {
                "code": item.code,
                "title": item.title,
                "summary": item.summary,
                "show_time": item.show_time,
                "real_sort": item.real_sort,
                "url": item.url,
                "author": item.author,
                "source": item.source,
                "content_text": item.content_text,
            }
            for item in state.article_pending_items
        ],
        "current_article_batch_day": state.current_article_batch_day,
        "current_article_batch_dir_name": state.current_article_batch_dir_name,
        "current_article_batch_item_count": state.current_article_batch_item_count,
    }
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f"{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp_name = handle.name
    os.replace(temp_name, path)
