from pathlib import Path
import json

from eastmoney_kuaixun.client import parse_count_payload, parse_list_payload
from eastmoney_kuaixun.config import load_settings
from eastmoney_kuaixun.daemon import run_collection_cycle
from eastmoney_kuaixun.models import ArticleDetail, CollectorState, FastNewsItem
from eastmoney_kuaixun.state import load_state, save_state


class FixtureClient:
    def __init__(self, count_payload: dict, list_payload: dict) -> None:
        self.count_payload = count_payload
        self.list_payload = list_payload
        self.calls = 0

    def fetch_increment_count(self, sort_start: str) -> int:
        self.calls += 1
        return parse_count_payload(self.count_payload)

    def fetch_latest_items(self, sort_end: str):
        return parse_list_payload(self.list_payload)

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
            content_text=f"body-{item.code}",
        )


def test_integration_flow_first_run_writes_then_second_run_skips(tmp_path: Path) -> None:
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    count_payload = json.loads(Path("tests/fixtures/count_payload.json").read_text(encoding="utf-8"))
    list_payload = json.loads(Path("tests/fixtures/list_payload.json").read_text(encoding="utf-8"))
    settings = load_settings(tmp_path)
    client = FixtureClient(count_payload, list_payload)

    initial_state = CollectorState()
    first = run_collection_cycle(client, settings, initial_state, empty_rounds=0, failure_count=0)
    save_state(settings.state_file, first.state)
    assert first.written == 2
    assert first.state.article_batch_index == 1
    assert first.state.current_article_batch_item_count == 2

    second = run_collection_cycle(client, settings, load_state(settings.state_file), empty_rounds=0, failure_count=0)
    assert second.written == 0
    assert second.state.article_batch_index == 1
    assert second.state.current_article_batch_item_count == 2
