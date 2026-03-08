from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

EASTMONEY_YW_COLUMN = "101"
DEFAULT_PAGE_SIZE = 20
DEFAULT_RECENT_IDS_LIMIT = 1000
DEFAULT_IDLE_THRESHOLD = 3


@dataclass(frozen=True)
class PollIntervalRange:
    minimum_seconds: int
    maximum_seconds: int


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    raw_dir: Path
    articles_dir: Path
    state_dir: Path
    state_file: Path
    normal_poll_range: PollIntervalRange
    idle_poll_range: PollIntervalRange
    backoff_schedule_seconds: tuple[int, ...]
    page_size: int
    recent_ids_limit: int
    idle_threshold: int
    user_agent: str


def resolve_data_dir(base_dir: Path | None = None) -> Path:
    if base_dir is not None:
        return base_dir
    env_dir = os.getenv("EASTMONEY_YW_DATA_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    return Path.cwd() / "data"


def load_settings(base_dir: Path | None = None) -> Settings:
    data_dir = resolve_data_dir(base_dir)
    raw_dir = data_dir / "raw"
    articles_dir = data_dir / "articles"
    state_dir = data_dir / "state"
    state_file = state_dir / "eastmoney-yw-state.json"
    return Settings(
        data_dir=data_dir,
        raw_dir=raw_dir,
        articles_dir=articles_dir,
        state_dir=state_dir,
        state_file=state_file,
        normal_poll_range=PollIntervalRange(minimum_seconds=30, maximum_seconds=90),
        idle_poll_range=PollIntervalRange(minimum_seconds=60, maximum_seconds=180),
        backoff_schedule_seconds=(180, 300, 600, 900),
        page_size=DEFAULT_PAGE_SIZE,
        recent_ids_limit=DEFAULT_RECENT_IDS_LIMIT,
        idle_threshold=DEFAULT_IDLE_THRESHOLD,
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        ),
    )
