# EastMoney YW Collector

用于后台增量抓取东方财富焦点快讯 `https://kuaixun.eastmoney.com/yw.html`，并按月写入本地 Markdown。

## 运行要求

- Python `>=3.12`
- `uv`

## 使用方式

进入项目目录：

```bash
cd /Users/moyueheng/.openclaw/workspace/input
```

执行单轮采集：

```bash
uv run eastmoney-yw
```

手动强制抓取最新一批并追加写入：

```bash
uv run eastmoney-yw --force-refresh
```

前台常驻运行：

```bash
uv run eastmoney-yw --daemon
```

指定自定义数据目录：

```bash
uv run eastmoney-yw --data-dir /path/to/data
```

## 输出目录

- `data/raw/`：按月归档的 Markdown 快讯文件
- `data/articles/`：按天和批次归档的正文文件，每个批次目录最多 5 条正文
- `data/state/`：采集状态文件和后台日志

说明：

- 默认执行会走增量轮询逻辑，若没有新增则不会重复写入
- `--force-refresh` 会忽略当前 state 一次，重新抓取最新列表并追加写入，因此可能在月度 Markdown 和正文目录中产生重复条目；适合手动补抓或验证正文落盘

示例：

- [data/raw](/Users/moyueheng/.openclaw/workspace/input/data/raw)
- [data/articles](/Users/moyueheng/.openclaw/workspace/input/data/articles)
- [data/state](/Users/moyueheng/.openclaw/workspace/input/data/state)

正文目录示例：

```text
data/articles/2026-03-08/20260308-083703_0001/
├── 01-202603083665282988.md
├── 02-...
└── ...
```

规则：

- 正文抓取成功后会立即写入当前批次目录
- 新闻日期变化时会立即切到新的日期目录和新批次
- 一个批次目录最多 5 条
- 当前目录写满 5 条后，下一条新闻会创建新目录

## macOS 后台自动获取

项目已提供：

- 启动脚本：[scripts/run-eastmoney-yw.sh](/Users/moyueheng/.openclaw/workspace/input/scripts/run-eastmoney-yw.sh)
- `launchd` 配置：[deploy/macos/com.myhron.eastmoney-yw.plist](/Users/moyueheng/.openclaw/workspace/input/deploy/macos/com.myhron.eastmoney-yw.plist)

安装并启动：

```bash
mkdir -p ~/Library/LaunchAgents
cp /Users/moyueheng/.openclaw/workspace/input/deploy/macos/com.myhron.eastmoney-yw.plist ~/Library/LaunchAgents/
launchctl unload ~/Library/LaunchAgents/com.myhron.eastmoney-yw.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.myhron.eastmoney-yw.plist
launchctl start com.myhron.eastmoney-yw
```

查看运行状态：

```bash
launchctl list | rg eastmoney-yw
tail -f /Users/moyueheng/.openclaw/workspace/input/data/state/eastmoney-yw.stdout.log
tail -f /Users/moyueheng/.openclaw/workspace/input/data/state/eastmoney-yw.stderr.log
```

停止并卸载：

```bash
launchctl stop com.myhron.eastmoney-yw
launchctl unload ~/Library/LaunchAgents/com.myhron.eastmoney-yw.plist
```

## Windows 后台自动获取

项目已提供：

- 启动脚本：[scripts/run-eastmoney-yw.bat](/Users/moyueheng/.openclaw/workspace/input/scripts/run-eastmoney-yw.bat)
- 安装脚本：[deploy/windows/install-task.ps1](/Users/moyueheng/.openclaw/workspace/input/deploy/windows/install-task.ps1)
- 卸载脚本：[deploy/windows/uninstall-task.ps1](/Users/moyueheng/.openclaw/workspace/input/deploy/windows/uninstall-task.ps1)

安装计划任务：

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\moyueheng\.openclaw\workspace\input\deploy\windows\install-task.ps1
```

卸载计划任务：

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\moyueheng\.openclaw\workspace\input\deploy\windows\uninstall-task.ps1
```

## 停止方式

- 前台运行时：`Ctrl+C`
- macOS 后台：`launchctl stop com.myhron.eastmoney-yw`
- Windows 后台：执行 `uninstall-task.ps1`
