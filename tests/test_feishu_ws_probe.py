from __future__ import annotations

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "feishu_ws_probe.py"
MODULE_SPEC = importlib.util.spec_from_file_location("feishu_ws_probe", MODULE_PATH)
assert MODULE_SPEC is not None
assert MODULE_SPEC.loader is not None
feishu_ws_probe = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(feishu_ws_probe)


def test_parse_args_defaults_to_forever_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["feishu_ws_probe.py"])

    args = feishu_ws_probe.parse_args()

    assert isinstance(args, Namespace)
    assert args.duration_seconds is None


def test_parse_args_accepts_explicit_duration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["feishu_ws_probe.py", "--duration-seconds", "30"])

    args = feishu_ws_probe.parse_args()

    assert args.duration_seconds == 30


def test_main_reports_missing_sdk(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(feishu_ws_probe, "lark", None)
    monkeypatch.setattr(feishu_ws_probe, "ws_client_module", None)
    monkeypatch.setattr("sys.argv", ["feishu_ws_probe.py", "--app-id", "cli_xxx", "--app-secret", "sec_xxx"])

    exit_code = feishu_ws_probe.main()

    assert exit_code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert "lark-oapi" in payload["msg"]
