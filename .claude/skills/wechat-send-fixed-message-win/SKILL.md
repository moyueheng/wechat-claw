---
name: wechat-send-fixed-message-win
description: 向指定微信联系人或群发送固定消息（Windows UI Automation 版）。用户提出"给某人发一句话""给某群发固定文案"等需求时使用。基于 Windows UI Automation，比键盘模拟更稳定。
---

# WeChat Send Fixed Message (Windows)

使用本技能向单个联系人或群聊发送一条固定消息。基于 Windows UI Automation 技术，可直接定位微信 UI 元素，比键盘模拟更稳定可靠。

## Workflow

1. 提取参数
   - `target`: 联系人名或群名（例如 `黄旭`、`工作群`）。
   - `message`: 要发送的完整文本。

2. 执行发送
   - 运行 `scripts/send_fixed_message.py`：

```bash
uv run python .agents/skills/wechat-send-fixed-message-win/scripts/send_fixed_message.py \
  --target "黄旭" \
  --message "你好我是 \"智投助手\""
```

3. 结果确认
   - 脚本成功时会输出 `sent_to_target`。

## Constraints

- 默认按"直接发送"执行，不做草稿停留。
- 不改写用户提供的消息文本，不擅自润色。
- 若微信未运行、未登录或窗口被最小化，会返回错误。

## Troubleshooting

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 未找到微信窗口 | 微信未启动 | 启动微信并登录后重试 |
| 搜索失败 | 微信版本更新导致控件变化 | 尝试键盘模拟版本作为备选 |
| 消息未发送 | 窗口未激活 | 手动点击微信窗口，再重试 |

## 备选方案：键盘模拟

如果 UI Automation 版本在特定微信版本上失效，可使用键盘模拟版本：

```bash
uv run python .agents/skills/wechat-send-fixed-message-win/scripts/send_fixed_message_kb.py \
  --target "黄旭" \
  --message "你好"
```

键盘模拟版特点：
- 使用 `pyautogui` 模拟键盘事件
- 兼容性更强，不依赖 UI 控件结构
- 需要微信窗口可交互

## 测试

本项目采用 TDD（测试驱动开发）方式开发，包含完整的单元测试：

```bash
# 运行所有测试
uv run pytest .agents/skills/wechat-send-fixed-message-win/tests/ -v

# 运行单元测试（Mock 模式）
uv run pytest .agents/skills/wechat-send-fixed-message-win/tests/ -v -m "not integration"

# 运行集成测试（需要微信运行）
uv run pytest .agents/skills/wechat-send-fixed-message-win/tests/ -v -m integration
```

测试覆盖率：
- 参数解析测试
- 窗口查找测试
- 发送流程测试
- 错误处理测试
- 键盘模拟版本测试

## Technical Details

- 使用 `uiautomation` 库操作 Windows UI Automation API
- 支持多种微信窗口类名：
  - `WeChatMainWndForPC` - 传统微信版本
  - `Qt51514QWindowIcon` - 微信 3.x (Qt 框架版本)
- 使用 Ctrl+F 触发搜索功能，模拟人工操作流程
- 代码经过 17 个测试用例验证（15 passed, 2 skipped）
