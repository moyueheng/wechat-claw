#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import sys
from pathlib import Path
from typing import Final

import lark_oapi as lark
from lark_oapi.ws import client as ws_client_module

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
        description="Temporary Feishu websocket probe based on lark_oapi.ws.Client."
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
        default=20,
        help="How long to keep the websocket alive before exiting.",
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


def on_p2_im_message_receive(data: lark.im.v1.P2ImMessageReceiveV1) -> None:
    print(
        json.dumps(
            {
                "event": "p2_im_message_receive_v1",
                "payload": json.loads(lark.JSON.marshal(data)),
            },
            ensure_ascii=False,
        )
    )


def on_customized_event(data: lark.CustomizedEvent) -> None:
    print(
        json.dumps(
            {
                "event": "customized_event",
                "payload": json.loads(lark.JSON.marshal(data)),
            },
            ensure_ascii=False,
        )
    )


def build_event_handler() -> lark.EventDispatcherHandler:
    return (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_im_message_receive_v1(on_p2_im_message_receive)
        .register_p1_customized_event("message", on_customized_event)
        .build()
    )


async def run_probe(app_id: str, app_secret: str, duration_seconds: int, log_level: lark.LogLevel) -> None:
    client = lark.ws.Client(
        app_id,
        app_secret,
        event_handler=build_event_handler(),
        log_level=log_level,
    )
    await client._connect()
    asyncio.get_running_loop().create_task(client._ping_loop())

    print(
        json.dumps(
            {
                "status": "connected",
                "duration_seconds": duration_seconds,
                "note": "Connection established. Waiting for subscribed events.",
            },
            ensure_ascii=False,
        )
    )

    stop_event = asyncio.Event()

    def stop_handler(signum: int, _frame: object) -> None:
        print(json.dumps({"status": "signal", "signal": signum}, ensure_ascii=False))
        stop_event.set()

    previous_sigint = signal.signal(signal.SIGINT, stop_handler)
    previous_sigterm = signal.signal(signal.SIGTERM, stop_handler)

    try:
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=duration_seconds)
        except asyncio.TimeoutError:
            print(json.dumps({"status": "timeout", "duration_seconds": duration_seconds}, ensure_ascii=False))
    finally:
        signal.signal(signal.SIGINT, previous_sigint)
        signal.signal(signal.SIGTERM, previous_sigterm)
        await client._disconnect()
        print(json.dumps({"status": "disconnected"}, ensure_ascii=False))


def main() -> int:
    args = parse_args()

    try:
        app_id = require_value(args.app_id, env_name=DEFAULT_APP_ID_ENV)
        app_secret = require_value(args.app_secret, env_name=DEFAULT_APP_SECRET_ENV)
        log_level = getattr(lark.LogLevel, args.log_level)
    except ValueError as exc:
        print(json.dumps({"status": "error", "msg": str(exc)}, ensure_ascii=False))
        return 2

    try:
        ws_loop = ws_client_module.loop
        ws_loop.run_until_complete(run_probe(app_id, app_secret, args.duration_seconds, log_level))
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "type": type(exc).__name__,
                    "msg": str(exc),
                },
                ensure_ascii=False,
            )
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
