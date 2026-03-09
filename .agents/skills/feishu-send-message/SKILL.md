---
name: feishu-send-message
description: 使用 larksuite/oapi-sdk-python 向指定飞书个人或群发送文本消息。用户提出“给某个飞书用户发消息”“给某个飞书群发一句话”“用飞书 SDK 发通知”这类需求时使用。适用于已知接收者 ID 且要通过飞书服务端 API 直接发送消息的场景。
---

# Feishu Send Message

使用本技能向单个飞书用户或群聊发送一条文本消息，并返回消息 ID、群 ID 与接口日志 ID。

## Workflow

1. 提取参数
- `receive-id-type`: 接收者 ID 类型。
- `receive-id`: 接收者 ID。
- `user-name`: 用户名称，脚本会先查本地别名，再尝试用飞书开放接口解析到 `open_id`。
- `chat-name`: 群名称，脚本会先查本地别名，再尝试用飞书开放接口解析到 `chat_id`。
- `message`: 要发送的完整文本。
- `message-file`: 消息文件路径，与 `message` 二选一。
- `app-id` / `app-secret`: 若未显式提供，则从环境变量 `FEISHU_APP_ID` / `FEISHU_APP_SECRET` 读取；若进程环境缺失，则回退读取仓库根目录 `.env`。
- `FEISHU_USER_ALIAS_JSON`: 可选 JSON，形如 `{"张三":"ou_xxx"}`。
- `FEISHU_CHAT_ALIAS_JSON`: 可选 JSON，形如 `{"策略群":"oc_xxx"}`。

2. 选择接收者类型
- 个人消息优先使用 `open_id`，若调用方明确给出其他 ID 类型则按原样传入。
- 群消息使用 `chat_id`。
- 若给的是 `user-name`，先查 `FEISHU_USER_ALIAS_JSON`，未命中时再枚举当前应用可见用户并匹配名称。
- 若给的是 `chat-name`，先查 `FEISHU_CHAT_ALIAS_JSON`，未命中时再调用 `client.im.v1.chat.search(...)` 搜索群名。

3. 执行发送
- 直接运行脚本：

```bash
uv run --with lark-oapi python .agents/skills/feishu-send-message/scripts/send_message.py \
  --receive-id-type "chat_id" \
  --receive-id "oc_a0553eda9014c201e6969b478895c230" \
  --message "收盘后同步一下仓位变化。"
```

按群名发送：

```bash
FEISHU_CHAT_ALIAS_JSON='{"策略群":"oc_xxx"}' \
uv run --with lark-oapi python .agents/skills/feishu-send-message/scripts/send_message.py \
  --chat-name "策略群" \
  --message "收盘后同步一下仓位变化。"
```

或从文件读取消息：

```bash
uv run --with lark-oapi python .agents/skills/feishu-send-message/scripts/send_message.py \
  --receive-id-type "open_id" \
  --receive-id "ou_xxx" \
  --message-file "/absolute/path/to/message.txt"
```

4. 结果确认
- 脚本成功时输出一段 JSON，包含 `status=ok`、`message_id`、`chat_id`、`log_id`。
- 成功结果还会返回 `receive_id_type`、`receive_id`、`resolved_by`，用于确认是通过显式 ID、用户名还是群名解析出来的。
- 脚本失败时输出错误 JSON，并带上接口 `code`、`msg`、`log_id`。

## Constraints

- 仅发送 `text` 文本消息，不擅自改写用户文案。
- 必须使用 `lark-oapi` 包，不改成手写 HTTP。
- 默认使用 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET`；优先读进程环境，其次读仓库根目录 `.env`，仍缺失时可通过命令参数显式传入。
- 允许按名称解析，但命中多个候选时直接报歧义错误，不擅自挑一个发送。
- 当前机器人若没有通讯录字段权限，用户名自动解析可能只能拿到用户 ID、拿不到姓名；这时应优先配置 `FEISHU_USER_ALIAS_JSON`。

## Troubleshooting

- 若接口报鉴权错误，先核对应用是否具备消息发送权限，以及环境变量是否指向正确应用。
- 若接口提示接收者 ID 不存在，直接返回错误，不自动切换成别的 ID 类型重试。
- 若按用户名解析失败，优先检查机器人是否具备读取用户资料字段的权限；权限不足时用 `FEISHU_USER_ALIAS_JSON` 兜底。
- 若按群名解析失败，先确认机器人是否在目标群内，再重试。
- 若消息体包含换行或中文，保持原文；脚本会自动编码为飞书文本消息所需 JSON。
