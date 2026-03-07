---
name: wechat-send-fixed-message
description: 向指定微信联系人或群发送固定消息。用户提出“给某人发一句话”“给某群发固定文案”“代我发这条消息”等需求时使用。适用于当前环境中 AX 定位不稳定时的键盘事件兜底发送流程。
---

# WeChat Send Fixed Message

使用本技能向单个联系人或群聊发送一条固定消息，并在发送后做可见性确认。

## Workflow

1. 提取参数
- `target`: 联系人名或群名（例如 `Britty`、`年入百万`）。
- `message`: 要发送的完整文本。

2. 执行发送
- 运行 `scripts/send_fixed_message.py`：

```bash
uv run python .agents/skills/wechat-send-fixed-message/scripts/send_fixed_message.py \
  --target "Britty" \
  --message "你好, 我叫银月"
```

3. 结果确认
- 脚本成功时会输出 `sent_to_target`。
- 如需人工核验，追加截图：

```bash
screencapture -x /tmp/wechat_sent_check.png
```

## Constraints

- 默认按“直接发送”执行，不做草稿停留。
- 不改写用户提供的消息文本，不擅自润色。
- 若微信未运行、未登录或前台被系统拦截，直接返回错误并提示重试。

## Troubleshooting

- 如果发送失败，先重试一次同命令。
- 如果仍失败，确认微信窗口可交互，再重试。
