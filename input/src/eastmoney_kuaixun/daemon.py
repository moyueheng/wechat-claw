from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
from pathlib import Path
import argparse
import random
import sys
import time

from .article_writer import append_article_to_batch, build_article_batch_dir_name
from .client import EastMoneyClient
from .config import Settings, load_settings
from .models import ArticleDetail, CollectorState, FastNewsItem, PendingArticleBatchItem
from .state import load_state, save_state, trim_recent_ids
from .writer import append_items_to_markdown


@dataclass(frozen=True)
class CycleResult:
    count: int
    fetched: int
    written: int
    next_sleep_seconds: int
    state: CollectorState
    output_path: Path | None = None
    error: str = ""


def filter_new_items(
    items: list[FastNewsItem], last_real_sort: str, recent_ids: set[str]
) -> list[FastNewsItem]:
    filtered: list[FastNewsItem] = []
    for item in sorted(items, key=lambda current: int(current.real_sort)):
        if last_real_sort and int(item.real_sort) <= int(last_real_sort):
            continue
        if item.seen_key in recent_ids:
            continue
        filtered.append(item)
    return filtered


def compute_next_interval(
    settings: Settings,
    empty_rounds: int,
    failure_count: int,
    rng: random.Random,
) -> int:
    if failure_count > 0:
        index = min(failure_count - 1, len(settings.backoff_schedule_seconds) - 1)
        return settings.backoff_schedule_seconds[index]
    poll_range = (
        settings.idle_poll_range
        if empty_rounds >= settings.idle_threshold
        else settings.normal_poll_range
    )
    return rng.randint(poll_range.minimum_seconds, poll_range.maximum_seconds)


def collect_article_details(
    client: EastMoneyClient, items: list[FastNewsItem]
) -> list[ArticleDetail]:
    details: list[ArticleDetail] = []
    for item in items:
        details.append(client.fetch_article_detail(item))
    return details


def write_articles_to_open_batches(
    articles_dir: Path,
    items: list[PendingArticleBatchItem],
    state: CollectorState,
) -> tuple[int, str, str, int, dict[str, Path]]:
    next_batch_index = state.article_batch_index
    current_batch_day = state.current_article_batch_day
    current_batch_dir_name = state.current_article_batch_dir_name
    current_batch_item_count = state.current_article_batch_item_count
    written_article_files: dict[str, Path] = {}
    for item in items:
        item_day = item.show_time[:10]
        if (
            current_batch_item_count >= 5
            or not current_batch_dir_name
            or current_batch_day != item_day
        ):
            next_batch_index += 1
            current_batch_day = item_day
            current_batch_dir_name = build_article_batch_dir_name(item, next_batch_index)
            current_batch_item_count = 0
        current_batch_item_count += 1
        file_path = append_article_to_batch(
            articles_dir,
            item,
            batch_day=current_batch_day,
            batch_dir_name=current_batch_dir_name,
            position=current_batch_item_count,
        )
        written_article_files[item.seen_key] = file_path
    return (
        next_batch_index,
        current_batch_day,
        current_batch_dir_name,
        current_batch_item_count,
        written_article_files,
    )


def run_collection_cycle(
    client: EastMoneyClient,
    settings: Settings,
    state: CollectorState,
    empty_rounds: int,
    failure_count: int,
    rng: random.Random | None = None,
) -> CycleResult:
    cycle_rng = rng or random.Random()
    sort_start = state.last_real_sort or "0"
    count = client.fetch_increment_count(sort_start=sort_start)
    items = client.fetch_latest_items(sort_end="0")
    filtered = filter_new_items(items, state.last_real_sort, set(state.recent_ids))
    if not filtered:
        return CycleResult(
            count=count,
            fetched=len(items),
            written=0,
            next_sleep_seconds=compute_next_interval(
                settings, empty_rounds + 1, failure_count, cycle_rng
            ),
            state=state,
        )
    article_details = collect_article_details(client, filtered)
    article_items = [
        detail.to_pending_item() for detail in article_details
    ]
    (
        article_batch_index,
        current_article_batch_day,
        current_article_batch_dir_name,
        current_article_batch_item_count,
        written_article_files,
    ) = write_articles_to_open_batches(
        settings.articles_dir,
        article_items,
        state,
    )
    output_path = append_items_to_markdown(
        settings.raw_dir,
        filtered,
        article_file_paths=written_article_files,
    )
    new_recent_ids = trim_recent_ids(
        state.recent_ids + [item.seen_key for item in filtered],
        settings.recent_ids_limit,
    )
    new_state = CollectorState(
        last_real_sort=filtered[-1].real_sort,
        recent_ids=new_recent_ids,
        article_batch_index=article_batch_index,
        article_pending_items=[],
        current_article_batch_day=current_article_batch_day,
        current_article_batch_dir_name=current_article_batch_dir_name,
        current_article_batch_item_count=current_article_batch_item_count,
    )
    return CycleResult(
        count=count,
        fetched=len(items),
        written=len(filtered),
        next_sleep_seconds=compute_next_interval(settings, 0, 0, cycle_rng),
        state=new_state,
        output_path=output_path,
    )


def run_main_loop(
    settings: Settings,
    client: EastMoneyClient,
    once: bool,
    force_refresh: bool = False,
    sleep_func: Callable[[float], None] = time.sleep,
    rng: random.Random | None = None,
) -> int:
    state = load_state(settings.state_file)
    empty_rounds = 0
    failure_count = 0
    pending_force_refresh = force_refresh
    while True:
        try:
            cycle_state = state
            if pending_force_refresh:
                cycle_state = CollectorState(
                    last_real_sort="",
                    recent_ids=[],
                    article_batch_index=state.article_batch_index,
                    article_pending_items=[],
                    current_article_batch_day=state.current_article_batch_day,
                    current_article_batch_dir_name=state.current_article_batch_dir_name,
                    current_article_batch_item_count=state.current_article_batch_item_count,
                )
            result = run_collection_cycle(
                client=client,
                settings=settings,
                state=cycle_state,
                empty_rounds=empty_rounds,
                failure_count=failure_count,
                rng=rng,
            )
            pending_force_refresh = False
            if result.written > 0:
                save_state(settings.state_file, result.state)
                state = result.state
                empty_rounds = 0
            else:
                empty_rounds += 1
            failure_count = 0
            print(
                "cycle ok",
                f"count={result.count}",
                f"fetched={result.fetched}",
                f"written={result.written}",
                f"sleep={result.next_sleep_seconds}",
            )
        except Exception as exc:
            failure_count += 1
            next_sleep = compute_next_interval(settings, empty_rounds, failure_count, rng or random.Random())
            print(f"cycle error error={exc} sleep={next_sleep}", file=sys.stderr)
            if once:
                return 1
            sleep_func(next_sleep)
            continue
        if once:
            return 0
        sleep_func(result.next_sleep_seconds)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="EastMoney YW collector")
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="run in a long-lived loop instead of a single cycle",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="override data directory",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="ignore current state once and append the latest list again",
    )
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()
    settings = load_settings(args.data_dir)
    print(
        "starting eastmoney-yw",
        f"data_dir={settings.data_dir}",
        f"state_file={settings.state_file}",
        f"mode={'daemon' if args.daemon else 'once'}",
        f"force_refresh={args.force_refresh}",
    )
    client = EastMoneyClient(settings=settings)
    return run_main_loop(
        settings=settings,
        client=client,
        once=not args.daemon,
        force_refresh=args.force_refresh,
    )


if __name__ == "__main__":
    raise SystemExit(main())
