from pathlib import Path

from eastmoney_kuaixun.models import CollectorState, PendingArticleBatchItem
from eastmoney_kuaixun.state import load_state, save_state, trim_recent_ids


def test_load_state_returns_default_when_missing(tmp_path: Path) -> None:
    state = load_state(tmp_path / "missing.json")
    assert state.last_real_sort == ""
    assert state.recent_ids == []


def test_save_and_load_state_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    save_state(path, CollectorState(last_real_sort="12", recent_ids=["x"]))
    state = load_state(path)
    assert state.last_real_sort == "12"
    assert state.recent_ids == ["x"]


def test_trim_recent_ids_keeps_last_entries() -> None:
    assert trim_recent_ids(["a", "b", "c"], limit=2) == ["b", "c"]


def test_save_and_load_state_round_trip_with_article_pending_items(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    state = CollectorState(
        last_real_sort="12",
        recent_ids=["x"],
        article_batch_index=3,
        article_pending_items=[],
        current_article_batch_day="2026-03-08",
        current_article_batch_dir_name="20260308-083703_0003",
        current_article_batch_item_count=2,
    )
    save_state(path, state)
    loaded = load_state(path)
    assert loaded.article_batch_index == 3
    assert loaded.current_article_batch_day == "2026-03-08"
    assert loaded.current_article_batch_dir_name == "20260308-083703_0003"
    assert loaded.current_article_batch_item_count == 2
