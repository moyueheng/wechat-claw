# wechat-claw 项目指南

> 面向 AI 编码助手：本文档记录项目架构、技术栈及开发约定。阅读本文件后再进行任何代码修改。

---

## 项目概述

**wechat-claw** 是一个基于 macOS 的微信自动化工具，通过模拟键盘事件实现消息发送功能。该项目主要作为 Kimi AI Agent 的 Skill 使用，用于在 Accessibility API (AX) 不稳定时提供兜底的消息发送能力。

- **项目名称**: wechat-claw
- **版本**: 0.1.0
- **平台**: macOS 专属（依赖 PyObjC 框架）
- **Python 版本**: >= 3.12

### 核心功能

项目主要提供一个 AI Agent Skill `wechat-send-fixed-message`，功能包括：
- 向指定微信联系人或群聊发送固定消息
- 通过键盘事件模拟实现（Cmd+F 搜索 → Cmd+V 粘贴 → Enter 发送）
- 发送结果确认与错误处理

---

## 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 包管理 | [UV](https://docs.astral.sh/uv/) | 现代 Python 包管理工具 |
| Python 版本 | 3.12 | 由 `.python-version` 指定 |
| macOS 集成 | PyObjC | 通过 Cocoa 和 Quartz 框架与 macOS 交互 |
| 核心依赖 | `pyobjc-framework-cocoa` | 访问 NSPasteboard、NSRunningApplication 等 |
| 核心依赖 | `pyobjc-framework-quartz` | 创建和发送键盘事件 (CGEvent) |

### 依赖详情

```toml
# pyproject.toml 关键依赖
[project]
requires-python = ">=3.12"
dependencies = [
    "pyobjc-framework-cocoa>=12.1",
    "pyobjc-framework-quartz>=12.1",
]

[[tool.uv.index]]
url = "https://pypi.tuna.tsinghua.edu.cn/simple"
default = true
```

> 注：使用清华 PyPI 镜像源加速依赖下载。

---

## 项目结构

```
.
├── .agents/
│   └── skills/
│       └── wechat-send-fixed-message/     # AI Agent Skill 目录
│           ├── SKILL.md                   # Skill 使用文档
│           ├── agents/
│           │   └── openai.yaml            # Agent 配置（显示名称、默认提示词）
│           └── scripts/
│               └── send_fixed_message.py  # 消息发送核心实现
├── .venv/                                 # UV 虚拟环境（自动生成）
├── .python-version                        # Python 版本: 3.12
├── main.py                                # 项目入口（当前为占位符）
├── pyproject.toml                         # 项目配置与依赖
├── README.md                              # 项目说明（当前为空）
└── uv.lock                                # 依赖锁定文件
```

---

## 构建与运行命令

### 环境准备

```bash
# 确保已安装 UV
which uv

# 创建虚拟环境并安装依赖
uv sync
```

### 运行主程序

```bash
# 运行主入口（当前仅输出 "Hello from wechat-claw!"）
uv run python main.py
```

### 运行 Skill 脚本

```bash
# 发送固定消息到指定联系人/群组
uv run python .agents/skills/wechat-send-fixed-message/scripts/send_fixed_message.py \
  --target "联系人名称" \
  --message "要发送的消息内容"
```

### 发送后截图确认

```bash
screencapture -x /tmp/wechat_sent_check.png
```

---

## 代码组织

### 模块划分

| 模块 | 路径 | 职责 |
|------|------|------|
| 核心 Skill 脚本 | `.agents/skills/wechat-send-fixed-message/scripts/send_fixed_message.py` | 微信消息发送的核心实现（macOS） |
| Skill 配置 | `.agents/skills/wechat-send-fixed-message/agents/openai.yaml` | Agent 界面配置 |
| Skill 文档 | `.agents/skills/wechat-send-fixed-message/SKILL.md` | Skill 使用说明与工作流 |
| Windows Skill 脚本 | `.agents/skills/wechat-send-fixed-message-win/scripts/send_fixed_message.py` | 微信消息发送（Windows UI Automation 版） |
| Windows 键盘版 | `.agents/skills/wechat-send-fixed-message-win/scripts/send_fixed_message_kb.py` | 微信消息发送（Windows 键盘模拟版） |
| Windows Skill 文档 | `.agents/skills/wechat-send-fixed-message-win/SKILL.md` | Windows 版使用说明 |
| 项目入口 | `main.py` | 项目主入口（待扩展） |

### 核心函数说明

**`send_fixed_message.py`** 中的关键函数：

```python
def key_tap(keycode: int, flags: int = 0) -> None
# 模拟单个按键敲击（按下+释放）
# 使用 Quartz 的 CGEventCreateKeyboardEvent 创建事件

def paste_text(text: str) -> None
# 将文本写入剪贴板，然后模拟 Cmd+V 粘贴
# 依赖: NSPasteboard

def send_fixed_message(target: str, message: str) -> None
# 完整发送流程：
# 1. 检查微信是否运行，未运行则报错
# 2. 激活微信窗口（activateWithOptions_）
# 3. Cmd+F 打开搜索
# 4. 粘贴并搜索目标联系人
# 5. Enter 打开聊天窗口
# 6. 粘贴消息内容
# 7. Enter 发送
```

---

## 开发约定

### 代码风格

- **类型注解**: 必须使用（如 `def foo() -> int:`）
- **导入风格**: 使用 `from __future__ import annotations` 启用延迟注解求值
- **函数命名**: 小写 + 下划线（snake_case）
- **常量定义**: 关键码使用内联注释说明（如 `key_tap(36, 0)  # Enter`）

### 时间延迟约定

脚本中包含多个 `time.sleep()` 调用，用于等待 UI 响应：
- 激活窗口后: 250ms
- 搜索后: 200ms
- 粘贴目标后: 300ms
- 粘贴消息后: 120ms
- 粘贴操作内部: 80ms

**注意**: 修改这些延迟可能影响脚本稳定性。

---

## 测试策略

### 当前状态

- 暂无为该项目编写自动化测试
- 测试依赖手动执行 Skill 脚本并观察结果

### 手动测试流程

1. 确保微信已登录并运行
2. 执行发送命令到测试联系人
3. 验证消息是否成功发送
4. 如失败，检查微信窗口是否可交互

### 建议添加的测试

- 微信运行状态检测测试
- 剪贴板操作测试
- 键盘事件模拟测试（需要 mocking Quartz API）

---

## 安全与权限考虑

### macOS 权限要求

该工具需要以下 macOS 权限才能正常工作：

1. **辅助功能 (Accessibility)** - 用于控制其他应用（微信）
   - 系统设置 → 隐私与安全 → 辅助功能 → 添加终端/IDE

2. **屏幕录制** - 如需使用截图确认功能
   - 系统设置 → 隐私与安全 → 屏幕录制

### 运行时检查

脚本会在以下情况抛出 `RuntimeError`:
- 微信未运行 (`"WeChat is not running"`)

### 安全注意事项

- 脚本通过剪贴板中转消息内容，敏感信息可能在剪贴板中短暂存在
- 键盘事件是系统级操作，可能影响其他应用
- 确保微信窗口在前台可交互时再执行发送

---

## 故障排查

### 常见问题

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 消息未发送 | 微信未在前台/被拦截 | 手动点击微信窗口，重试 |
| 搜索失败 | 延迟不足 | 适当增加 `time.sleep()` 时长 |
| 粘贴失败 | 剪贴板权限 | 检查辅助功能权限 |
| 运行时错误 | 微信未启动 | 启动微信并登录后重试 |

### 调试建议

1. 首次使用先在测试联系人上验证
2. 发送失败后先重试一次相同命令
3. 使用 `screencapture` 截图确认 UI 状态

---

## 扩展指南

### 添加新的 Skill

在 `.agents/skills/` 下创建新目录，结构如下：

```
new-skill/
├── SKILL.md              # 文档，包含使用示例
├── agents/
│   └── openai.yaml       # Agent 配置
└── scripts/
    └── script.py         # 实现脚本
```

### 扩展现有功能

修改 `send_fixed_message.py` 时需注意：
1. 保持现有的错误处理模式
2. 新的键盘操作需要适当的时间延迟
3. 更新 `SKILL.md` 中的使用示例

---

## 作者

- **myhron** <moyueheng@gmail.com>
