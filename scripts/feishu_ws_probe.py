#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import sys
from pathlib import Path
from typing import Any, Final

try:
    import lark_oapi as lark
    from lark_oapi.ws import client as ws_client_module
except ModuleNotFoundError:
    lark = None
    ws_client_module = None

DEFAULT_APP_ID_ENV: Final[str] = "FEISHU_APP_ID"
DEFAULT_APP_SECRET_ENV: Final[str] = "FEISHU_APP_SECRET"
REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH: Final[Path] = REPO_ROOT / ".env"


def load_dotenv_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        os.environ.setdefault(key, value.strip())


load_dotenv_file(DEFAULT_ENV_PATH)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a Feishu websocket client for the current bot."
    )
    parser.add_argument(
        "--app-id",
        default=os.getenv(DEFAULT_APP_ID_ENV),
        help=f"Feishu app id. Defaults to ${DEFAULT_APP_ID_ENV} or repo .env.",
    )
    parser.add_argument(
        "--app-secret",
        default=os.getenv(DEFAULT_APP_SECRET_ENV),
        help=f"Feishu app secret. Defaults to ${DEFAULT_APP_SECRET_ENV} or repo .env.",
    )
    parser.add_argument(
        "--duration-seconds",
        type=int,
        default=None,
        help="Optional timeout. Omit it to keep the long connection alive until a signal arrives.",
    )
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARN", "ERROR"),
        default="INFO",
        help="SDK log level.",
    )
    return parser.parse_args()


def require_value(value: str | None, *, env_name: str) -> str:
    if value:
        return value
    raise ValueError(f"Missing credential. Set {env_name} or pass the CLI flag explicitly.")


def ensure_sdk_available() -> None:
    if lark is not None and ws_client_module is not None:
        return
    raise ValueError(
        "Missing dependency: lark-oapi. Install project dependencies or run with `uv run --with lark-oapi`."
    )


def emit_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def on_p2_im_message_receive(data: Any) -> None:
    emit_json(
        {
            "event": "p2_im_message_receive_v1",
            "payload": json.loads(lark.JSON.marshal(data)),
        }
    )


def on_customized_event(data: Any) -> None:
    emit_json(
        {
            "event": "customized_event",
            "payload": json.loads(lark.JSON.marshal(data)),
        }
    )


def build_event_handler() -> Any:
    return (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_im_message_receive_v1(on_p2_im_message_receive)
        .register_p1_customized_event("message", on_customized_event)
        .build()
    )


async def wait_for_shutdown(duration_seconds: int | None) -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def stop_handler(signum: int, _frame: object) -> None:
        emit_json({"status": "signal", "signal": signum})
        loop.call_soon_threadsafe(stop_event.set)

    previous_sigint = signal.signal(signal.SIGINT, stop_handler)
    previous_sigterm = signal.signal(signal.SIGTERM, stop_handler)

    try:
        if duration_seconds is None:
            await stop_event.wait()
            return

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=duration_seconds)
        except asyncio.TimeoutError:
            emit_json({"status": "timeout", "duration_seconds": duration_seconds})
    finally:
        signal.signal(signal.SIGINT, previous_sigint)
        signal.signal(signal.SIGTERM, previous_sigterm)


async def run_probe(app_id: str, app_secret: str, duration_seconds: int | None, log_level: Any) -> None:
    client = lark.ws.Client(
        app_id,
        app_secret,
        event_handler=build_event_handler(),
        log_level=log_level,
    )
    await client._connect()
    asyncio.get_running_loop().create_task(client._ping_loop())

    emit_json(
        {
            "status": "connected",
            "duration_seconds": duration_seconds,
            "mode": "forever" if duration_seconds is None else "timeout",
            "note": "Connection established. Waiting for subscribed events.",
        }
    )

    try:
        await wait_for_shutdown(duration_seconds)
    finally:
        await client._disconnect()
        emit_json({"status": "disconnected"})


def main() -> int:
    args = parse_args()

    try:
        ensure_sdk_available()
        app_id = require_value(args.app_id, env_name=DEFAULT_APP_ID_ENV)
        app_secret = require_value(args.app_secret, env_name=DEFAULT_APP_SECRET_ENV)
        log_level = getattr(lark.LogLevel, args.log_level)
    except ValueError as exc:
        emit_json({"status": "error", "msg": str(exc)})
        return 2

    try:
        ws_loop = ws_client_module.loop
        ws_loop.run_until_complete(run_probe(app_id, app_secret, args.duration_seconds, log_level))
    except Exception as exc:
        emit_json(
            {
                "status": "error",
                "type": type(exc).__name__,
                "msg": str(exc),
            }
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
