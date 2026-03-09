#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Final
from uuid import uuid4

import lark_oapi as lark
from lark_oapi.api.contact.v3 import GetUserRequest, ListScopeRequest
from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
    CreateMessageResponse,
    SearchChatRequest,
)

DEFAULT_APP_ID_ENV: Final[str] = "FEISHU_APP_ID"
DEFAULT_APP_SECRET_ENV: Final[str] = "FEISHU_APP_SECRET"
USER_ALIAS_JSON_ENV: Final[str] = "FEISHU_USER_ALIAS_JSON"
CHAT_ALIAS_JSON_ENV: Final[str] = "FEISHU_CHAT_ALIAS_JSON"
REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[4]
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
        description="Use lark-oapi to send a text message to a Feishu user or group."
    )
    parser.add_argument("--receive-id-type", help="Feishu receive_id_type, such as open_id or chat_id.")
    parser.add_argument("--receive-id", help="Concrete receiver ID that matches --receive-id-type.")
    parser.add_argument("--user-name", help="Resolve a user by alias or visible profile name, then send to that open_id.")
    parser.add_argument("--chat-name", help="Resolve a chat by alias or official chat search, then send to that chat_id.")
    parser.add_argument("--message", help="Plain text message content.")
    parser.add_argument("--message-file", help="Path to a UTF-8 text file containing the message body.")
    parser.add_argument("--app-id", default=os.getenv(DEFAULT_APP_ID_ENV), help=f"Feishu app id. Defaults to ${DEFAULT_APP_ID_ENV} or repo .env.")
    parser.add_argument(
        "--app-secret",
        default=os.getenv(DEFAULT_APP_SECRET_ENV),
        help=f"Feishu app secret. Defaults to ${DEFAULT_APP_SECRET_ENV} or repo .env.",
    )
    return parser.parse_args()


def load_message(message: str | None, message_file: str | None) -> str:
    if bool(message) == bool(message_file):
        raise ValueError("Provide exactly one of --message or --message-file.")

    if message is not None:
        return message

    assert message_file is not None
    path = Path(message_file)
    return path.read_text(encoding="utf-8")


def require_secret(value: str | None, *, flag_name: str, env_name: str) -> str:
    if value:
        return value
    raise ValueError(f"Missing {flag_name}. Set it explicitly or export {env_name}.")


def parse_alias_map(raw_json: str | None, *, env_name: str) -> dict[str, str]:
    if raw_json is None or not raw_json.strip():
        return {}

    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{env_name} must be valid JSON object: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"{env_name} must be a JSON object mapping names to IDs.")

    result: dict[str, str] = {}
    for raw_key, raw_value in payload.items():
        key = str(raw_key).strip()
        value = str(raw_value).strip()
        if key and value:
            result[key] = value
    return result


def build_client(app_id: str, app_secret: str) -> lark.Client:
    return lark.Client.builder().app_id(app_id).app_secret(app_secret).build()


def normalize_name(value: str) -> str:
    return value.strip().casefold()


def choose_best_match(target_name: str, candidates: list[dict[str, str]]) -> dict[str, str]:
    normalized_target = normalize_name(target_name)
    exact = [item for item in candidates if normalize_name(item["matched_name"]) == normalized_target]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise ValueError(
            "Found multiple exact matches: "
            + json.dumps(exact, ensure_ascii=False)
        )

    partial = [
        item for item in candidates
        if normalized_target in normalize_name(item["matched_name"])
        or normalize_name(item["matched_name"]) in normalized_target
    ]
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        raise ValueError(
            "Found multiple partial matches: "
            + json.dumps(partial, ensure_ascii=False)
        )

    raise ValueError(f"No match found for name: {target_name}")


def resolve_user_name(client: lark.Client, user_name: str, alias_map: dict[str, str]) -> tuple[str, str]:
    alias_id = alias_map.get(user_name)
    if alias_id:
        return "open_id", alias_id

    page_token: str | None = None
    user_ids: list[str] = []
    while True:
        request_builder = (
            ListScopeRequest.builder()
            .user_id_type("open_id")
            .department_id_type("open_department_id")
            .page_size(50)
        )
        if page_token:
            request_builder = request_builder.page_token(page_token)
        response = client.contact.v3.scope.list(request_builder.build())
        if not response.success():
            raise ValueError(
                f"Failed to list visible users: code={response.code}, msg={response.msg}, log_id={response.get_log_id()}"
            )
        data = response.data
        user_ids.extend(getattr(data, "user_ids", None) or [])
        if not getattr(data, "has_more", False):
            break
        page_token = getattr(data, "page_token", None)
        if not page_token:
            break

    candidates: list[dict[str, str]] = []
    missing_profile_count = 0
    for user_id in user_ids:
        request = (
            GetUserRequest.builder()
            .user_id(user_id)
            .user_id_type("open_id")
            .department_id_type("open_department_id")
            .build()
        )
        response = client.contact.v3.user.get(request)
        if not response.success():
            continue
        user = getattr(response.data, "user", None)
        if user is None:
            continue
        visible_names = []
        for field_name in ("name", "nickname", "en_name", "email", "enterprise_email", "mobile"):
            value = getattr(user, field_name, None)
            if isinstance(value, str) and value.strip():
                visible_names.append(value.strip())
        if not visible_names:
            missing_profile_count += 1
            continue
        for visible_name in visible_names:
            candidates.append(
                {
                    "matched_name": visible_name,
                    "open_id": getattr(user, "open_id", None) or user_id,
                }
            )

    if not candidates and missing_profile_count:
        raise ValueError(
            "The app can see user IDs but cannot read profile names. "
            f"Configure {USER_ALIAS_JSON_ENV} or pass --receive-id directly."
        )

    chosen = choose_best_match(user_name, candidates)
    return "open_id", chosen["open_id"]


def resolve_chat_name(client: lark.Client, chat_name: str, alias_map: dict[str, str]) -> tuple[str, str]:
    alias_id = alias_map.get(chat_name)
    if alias_id:
        return "chat_id", alias_id

    page_token: str | None = None
    candidates: list[dict[str, str]] = []
    while True:
        request_builder = (
            SearchChatRequest.builder()
            .user_id_type("open_id")
            .query(chat_name)
            .page_size(50)
        )
        if page_token:
            request_builder = request_builder.page_token(page_token)
        response = client.im.v1.chat.search(request_builder.build())
        if not response.success():
            raise ValueError(
                f"Failed to search chats: code={response.code}, msg={response.msg}, log_id={response.get_log_id()}"
            )
        items = getattr(response.data, "items", None) or []
        for item in items:
            name = getattr(item, "name", None)
            chat_id = getattr(item, "chat_id", None)
            if isinstance(name, str) and name.strip() and isinstance(chat_id, str) and chat_id.strip():
                candidates.append({"matched_name": name.strip(), "chat_id": chat_id.strip()})
        if not getattr(response.data, "has_more", False):
            break
        page_token = getattr(response.data, "page_token", None)
        if not page_token:
            break

    chosen = choose_best_match(chat_name, candidates)
    return "chat_id", chosen["chat_id"]


def resolve_target(
    client: lark.Client,
    *,
    receive_id_type: str | None,
    receive_id: str | None,
    user_name: str | None,
    chat_name: str | None,
    user_alias_map: dict[str, str],
    chat_alias_map: dict[str, str],
) -> tuple[str, str, str]:
    name_flags = [flag for flag in (user_name, chat_name) if flag]
    if receive_id or receive_id_type:
        if name_flags:
            raise ValueError("Use either explicit receive ID flags or name-based flags, not both.")
        if not receive_id_type or not receive_id:
            raise ValueError("Both --receive-id-type and --receive-id are required together.")
        return receive_id_type, receive_id, "explicit-id"

    if user_name and chat_name:
        raise ValueError("Use only one of --user-name or --chat-name.")
    if user_name:
        resolved_type, resolved_id = resolve_user_name(client, user_name, user_alias_map)
        return resolved_type, resolved_id, "user-name"
    if chat_name:
        resolved_type, resolved_id = resolve_chat_name(client, chat_name, chat_alias_map)
        return resolved_type, resolved_id, "chat-name"

    raise ValueError(
        "Provide either --receive-id-type with --receive-id, or one of --user-name / --chat-name."
    )


def build_request(receive_id_type: str, receive_id: str, message: str) -> CreateMessageRequest:
    content = json.dumps({"text": message}, ensure_ascii=False)
    return (
        CreateMessageRequest.builder()
        .receive_id_type(receive_id_type)
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(receive_id)
            .msg_type("text")
            .content(content)
            .uuid(str(uuid4()))
            .build()
        )
        .build()
    )


def response_payload(
    response: CreateMessageResponse,
    *,
    receive_id_type: str,
    receive_id: str,
    resolved_by: str,
) -> dict[str, object | None]:
    data = response.data
    return {
        "status": "ok",
        "receive_id_type": receive_id_type,
        "receive_id": receive_id,
        "resolved_by": resolved_by,
        "message_id": getattr(data, "message_id", None),
        "chat_id": getattr(data, "chat_id", None),
        "msg_type": getattr(data, "msg_type", None),
        "log_id": response.get_log_id(),
    }


def error_payload(response: CreateMessageResponse) -> dict[str, object | None]:
    return {
        "status": "error",
        "code": response.code,
        "msg": response.msg,
        "log_id": response.get_log_id(),
    }


def main() -> int:
    args = parse_args()

    try:
        message = load_message(args.message, args.message_file)
        app_id = require_secret(args.app_id, flag_name="--app-id", env_name=DEFAULT_APP_ID_ENV)
        app_secret = require_secret(
            args.app_secret,
            flag_name="--app-secret",
            env_name=DEFAULT_APP_SECRET_ENV,
        )
        user_alias_map = parse_alias_map(os.getenv(USER_ALIAS_JSON_ENV), env_name=USER_ALIAS_JSON_ENV)
        chat_alias_map = parse_alias_map(os.getenv(CHAT_ALIAS_JSON_ENV), env_name=CHAT_ALIAS_JSON_ENV)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "error", "msg": str(exc)}, ensure_ascii=False))
        return 2

    client = build_client(app_id, app_secret)
    try:
        receive_id_type, receive_id, resolved_by = resolve_target(
            client,
            receive_id_type=args.receive_id_type,
            receive_id=args.receive_id,
            user_name=args.user_name,
            chat_name=args.chat_name,
            user_alias_map=user_alias_map,
            chat_alias_map=chat_alias_map,
        )
    except ValueError as exc:
        print(json.dumps({"status": "error", "msg": str(exc)}, ensure_ascii=False))
        return 2

    request = build_request(receive_id_type, receive_id, message)
    response = client.im.v1.message.create(request)

    if not response.success():
        print(json.dumps(error_payload(response), ensure_ascii=False))
        return 1

    print(
        json.dumps(
            response_payload(
                response,
                receive_id_type=receive_id_type,
                receive_id=receive_id,
                resolved_by=resolved_by,
            ),
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
