# EastMoney YW Markdown Collector Implementation Plan

> **给 Kimi：** 必需子 skill：使用 `dev-executing-plans` 逐个任务实施此计划。

**目标：** 构建一个跨平台的东方财富焦点快讯采集器，低频增量抓取 `fastColumn=101` 新闻，并将新增快讯稳定追加到本地 Markdown，支持 macOS 与 Windows 后台运行。

**架构：** 业务层采用一套 Python 常驻 CLI 进程，负责接口访问、去重、Markdown 落盘与状态持久化；托管层分别通过 macOS `launchd` 与 Windows `Task Scheduler` 拉起该进程。所有状态以本地 JSON 保存，Markdown 按月归档。

**技术栈：** Python 3.12、`uv`、`pytest`、标准库 `urllib/json/pathlib/random/time/dataclasses`，可选轻量 HTTP 库 `httpx` 或 `requests`，macOS `launchd`，Windows PowerShell + Task Scheduler。

---

### 任务 1：建立项目骨架与运行入口

**文件：**
- 创建：`/Users/moyueheng/.openclaw/workspace/pyproject.toml`
- 创建：`/Users/moyueheng/.openclaw/workspace/src/eastmoney_kuaixun/__init__.py`
- 创建：`/Users/moyueheng/.openclaw/workspace/src/eastmoney_kuaixun/config.py`
- 创建：`/Users/moyueheng/.openclaw/workspace/src/eastmoney_kuaixun/daemon.py`
- 创建：`/Users/moyueheng/.openclaw/workspace/scripts/run-eastmoney-yw.sh`
- 创建：`/Users/moyueheng/.openclaw/workspace/scripts/run-eastmoney-yw.bat`

**步骤 1：创建基础目录**

运行：

```bash
mkdir -p src/eastmoney_kuaixun tests/eastmoney_kuaixun data/raw data/state scripts deploy/macos deploy/windows
```

预期：目录创建完成，无报错。

**步骤 2：创建 `pyproject.toml`**

写入最小项目配置，包含：

- 项目名
- Python 版本约束 `>=3.12`
- 测试命令依赖 `pytest`
- 可执行入口，如 `eastmoney-yw = "eastmoney_kuaixun.daemon:main"`

**步骤 3：创建基础配置模块**

在 `config.py` 中定义：

- 栏目常量 `EASTMONEY_YW_COLUMN = "101"`
- 默认数据目录
- 默认轮询区间
- 默认退避区间
- 平台无关的路径解析函数

要求：

- 所有函数与数据结构都加类型注解
- 只放配置和路径逻辑，不放请求逻辑

**步骤 4：创建最小 CLI 入口**

在 `daemon.py` 中先放一个可执行 `main()`，先只打印启动信息和加载配置，不进入真正采集循环。

**步骤 5：创建平台启动脚本**

- `run-eastmoney-yw.sh` 调用 `uv run eastmoney-yw`
- `run-eastmoney-yw.bat` 调用等价的 Windows 命令

**步骤 6：验证入口可运行**

运行：

```bash
uv run eastmoney-yw
```

预期：程序启动并打印最小启动信息，退出码为 0。

### 任务 2：定义数据模型与状态模型

**文件：**
- 创建：`/Users/moyueheng/.openclaw/workspace/src/eastmoney_kuaixun/models.py`
- 创建：`/Users/moyueheng/.openclaw/workspace/tests/eastmoney_kuaixun/test_models.py`

> **给 Kimi：** 此任务使用 `dev-tdd` skill。遵循 RED-GREEN-REFACTOR。

**步骤 1：RED - 编写失败的测试**

**调用 dev-tdd**：为新闻记录和状态记录定义测试，至少覆盖：

```python
from eastmoney_kuaixun.models import FastNewsItem, CollectorState


def test_fast_news_item_seen_key_prefers_code_and_real_sort() -> None:
    item = FastNewsItem(
        code="123456789",
        title="title",
        summary="summary",
        show_time="2026-03-08 11:31:00",
        real_sort="1772939953000",
        url="https://finance.eastmoney.com/a/123456789.html",
    )
    assert item.seen_key == "123456789:1772939953000"


def test_collector_state_tracks_recent_ids() -> None:
    state = CollectorState(last_real_sort="10", recent_ids=["a", "b"])
    assert state.last_real_sort == "10"
    assert state.recent_ids == ["a", "b"]
```

**步骤 2：验证 RED - 看着它失败**

**调用 dev-tdd**：运行：

```bash
pytest tests/eastmoney_kuaixun/test_models.py -v
```

预期：FAIL，原因是 `models.py` 或相关符号尚不存在。

**步骤 3：GREEN - 编写最小实现**

**调用 dev-tdd**：在 `models.py` 中使用 `dataclass` 实现：

- `FastNewsItem`
- `CollectorState`
- `FastNewsItem.seen_key` 计算逻辑

要求：

- 字段全部显式声明类型
- 对缺失 `code` 的降级 key 规则清晰可测

**步骤 4：验证 GREEN - 看着它通过**

**调用 dev-tdd**：运行：

```bash
pytest tests/eastmoney_kuaixun/test_models.py -v
```

预期：PASS。

**步骤 5：REFACTOR（可选）**

**调用 dev-tdd**：检查命名是否清晰，避免把解析逻辑提前塞进模型层。

### 任务 3：实现状态持久化

**文件：**
- 创建：`/Users/moyueheng/.openclaw/workspace/src/eastmoney_kuaixun/state.py`
- 创建：`/Users/moyueheng/.openclaw/workspace/tests/eastmoney_kuaixun/test_state.py`

> **给 Kimi：** 此任务使用 `dev-tdd` skill。遵循 RED-GREEN-REFACTOR。

**步骤 1：RED - 编写失败的测试**

**调用 dev-tdd**：编写测试覆盖：

- state 文件不存在时返回默认状态
- state 可写入并再次读回
- recent_ids 会被裁剪到固定窗口

示例测试：

```python
from pathlib import Path

from eastmoney_kuaixun.state import load_state, save_state
from eastmoney_kuaixun.models import CollectorState


def test_load_state_returns_default_when_missing(tmp_path: Path) -> None:
    state = load_state(tmp_path / "missing.json")
    assert state.last_real_sort == ""
    assert state.recent_ids == []


def test_save_and_load_state_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    save_state(path, CollectorState(last_real_sort="12", recent_ids=["x"]))
    state = load_state(path)
    assert state.last_real_sort == "12"
    assert state.recent_ids == ["x"]
```

**步骤 2：验证 RED - 看着它失败**

**调用 dev-tdd**：运行：

```bash
pytest tests/eastmoney_kuaixun/test_state.py -v
```

预期：FAIL。

**步骤 3：GREEN - 编写最小实现**

**调用 dev-tdd**：在 `state.py` 中实现：

- `load_state(path: Path) -> CollectorState`
- `save_state(path: Path, state: CollectorState) -> None`
- `trim_recent_ids(recent_ids: list[str], limit: int) -> list[str]`

要求：

- 使用 JSON
- 自动创建父目录
- 写入采用原子替换策略，避免中途损坏

**步骤 4：验证 GREEN - 看着它通过**

**调用 dev-tdd**：运行：

```bash
pytest tests/eastmoney_kuaixun/test_state.py -v
```

预期：PASS。

**步骤 5：REFACTOR（可选）**

**调用 dev-tdd**：确认状态模块不依赖网络层与 Markdown 层。

### 任务 4：实现 Markdown 写入器

**文件：**
- 创建：`/Users/moyueheng/.openclaw/workspace/src/eastmoney_kuaixun/writer.py`
- 创建：`/Users/moyueheng/.openclaw/workspace/tests/eastmoney_kuaixun/test_writer.py`

> **给 Kimi：** 此任务使用 `dev-tdd` skill。遵循 RED-GREEN-REFACTOR。

**步骤 1：RED - 编写失败的测试**

**调用 dev-tdd**：覆盖：

- 按月选择输出文件
- 首次写入会生成头部
- 同一天多条新闻会放在同一日期段下
- 条目格式包含时间、正文、`code`、`real_sort`、`url`

示例测试：

```python
from pathlib import Path

from eastmoney_kuaixun.models import FastNewsItem
from eastmoney_kuaixun.writer import append_items_to_markdown


def test_append_items_creates_monthly_markdown(tmp_path: Path) -> None:
    item = FastNewsItem(
        code="123",
        title="title",
        summary="summary",
        show_time="2026-03-08 11:31:00",
        real_sort="100",
        url="https://finance.eastmoney.com/a/123.html",
    )
    output = append_items_to_markdown(tmp_path, [item])
    content = output.read_text(encoding="utf-8")
    assert output.name == "eastmoney-yw-2026-03.md"
    assert "## 2026-03-08" in content
    assert "### 11:31" in content
    assert "- real_sort: 100" in content
```

**步骤 2：验证 RED - 看着它失败**

**调用 dev-tdd**：运行：

```bash
pytest tests/eastmoney_kuaixun/test_writer.py -v
```

预期：FAIL。

**步骤 3：GREEN - 编写最小实现**

**调用 dev-tdd**：在 `writer.py` 中实现：

- 月度文件路径解析
- Markdown 头部生成
- 日期分组与条目渲染
- 追加写入

要求：

- 不重复写全文件头
- 输出保持 UTF-8
- 仅做文件写入，不做去重判断

**步骤 4：验证 GREEN - 看着它通过**

**调用 dev-tdd**：运行：

```bash
pytest tests/eastmoney_kuaixun/test_writer.py -v
```

预期：PASS。

**步骤 5：REFACTOR（可选）**

**调用 dev-tdd**：提取渲染辅助函数，避免 `append` 函数过长。

### 任务 5：实现东方财富客户端

**文件：**
- 创建：`/Users/moyueheng/.openclaw/workspace/src/eastmoney_kuaixun/client.py`
- 创建：`/Users/moyueheng/.openclaw/workspace/tests/eastmoney_kuaixun/test_client.py`

> **给 Kimi：** 此任务使用 `dev-tdd` skill。遵循 RED-GREEN-REFACTOR。

**步骤 1：RED - 编写失败的测试**

**调用 dev-tdd**：用假响应样本测试：

- 解析 `count` 响应
- 解析 `list` 响应为 `FastNewsItem`
- 跳过缺少 `realSort` 的脏数据

示例测试：

```python
from eastmoney_kuaixun.client import parse_count_payload, parse_list_payload


def test_parse_count_payload_reads_increment_count() -> None:
    payload = {"data": {"count": 3}}
    assert parse_count_payload(payload) == 3


def test_parse_list_payload_returns_fast_news_items() -> None:
    payload = {
        "data": {
            "fastNewsList": [
                {
                    "code": "123",
                    "title": "title",
                    "summary": "summary",
                    "showTime": "2026-03-08 11:31:00",
                    "realSort": "100",
                }
            ]
        }
    }
    items = parse_list_payload(payload)
    assert len(items) == 1
    assert items[0].real_sort == "100"
```

**步骤 2：验证 RED - 看着它失败**

**调用 dev-tdd**：运行：

```bash
pytest tests/eastmoney_kuaixun/test_client.py -v
```

预期：FAIL。

**步骤 3：GREEN - 编写最小实现**

**调用 dev-tdd**：在 `client.py` 中实现：

- 接口 URL 构建函数
- `parse_count_payload`
- `parse_list_payload`
- 一个最小 HTTP 请求封装

要求：

- 不在这一层写轮询循环
- 请求头保持普通浏览器风格
- 单线程、单请求链路，不做并发

**步骤 4：验证 GREEN - 看着它通过**

**调用 dev-tdd**：运行：

```bash
pytest tests/eastmoney_kuaixun/test_client.py -v
```

预期：PASS。

**步骤 5：REFACTOR（可选）**

**调用 dev-tdd**：把 URL 构建和 payload 解析分开，保持模块边界明确。

### 任务 6：实现去重与轮询决策逻辑

**文件：**
- 修改：`/Users/moyueheng/.openclaw/workspace/src/eastmoney_kuaixun/daemon.py`
- 创建：`/Users/moyueheng/.openclaw/workspace/tests/eastmoney_kuaixun/test_daemon.py`

> **给 Kimi：** 此任务使用 `dev-tdd` skill。遵循 RED-GREEN-REFACTOR。

**步骤 1：RED - 编写失败的测试**

**调用 dev-tdd**：覆盖：

- `count=0` 时不请求列表
- 只保留 `real_sort > last_real_sort` 的新闻
- `recent_ids` 命中时跳过重复
- 正常状态下返回 `30-90 秒` 抖动区间
- 连续失败后进入退避

示例测试：

```python
from eastmoney_kuaixun.daemon import filter_new_items
from eastmoney_kuaixun.models import FastNewsItem


def test_filter_new_items_skips_old_and_duplicate_items() -> None:
    items = [
        FastNewsItem(code="a", title="t1", summary="s1", show_time="2026-03-08 11:31:00", real_sort="100", url="u1"),
        FastNewsItem(code="b", title="t2", summary="s2", show_time="2026-03-08 11:32:00", real_sort="101", url="u2"),
    ]
    result = filter_new_items(items, last_real_sort="100", recent_ids={"b:101"})
    assert result == []
```

**步骤 2：验证 RED - 看着它失败**

**调用 dev-tdd**：运行：

```bash
pytest tests/eastmoney_kuaixun/test_daemon.py -v
```

预期：FAIL。

**步骤 3：GREEN - 编写最小实现**

**调用 dev-tdd**：在 `daemon.py` 中实现：

- `filter_new_items`
- 轮询间隔与退避计算
- 一轮采集流程编排函数

要求：

- 先 `count`，后 `list`
- 先落盘，后更新 state
- 一轮采集函数尽量可测试，不把所有逻辑塞进 `while True`

**步骤 4：验证 GREEN - 看着它通过**

**调用 dev-tdd**：运行：

```bash
pytest tests/eastmoney_kuaixun/test_daemon.py -v
```

预期：PASS。

**步骤 5：REFACTOR（可选）**

**调用 dev-tdd**：把“纯逻辑”和“真实 I/O”拆开，降低测试耦合度。

### 任务 7：集成主循环与日志输出

**文件：**
- 修改：`/Users/moyueheng/.openclaw/workspace/src/eastmoney_kuaixun/daemon.py`
- 创建：`/Users/moyueheng/.openclaw/workspace/tests/eastmoney_kuaixun/test_main_loop.py`

> **给 Kimi：** 此任务使用 `dev-tdd` skill。遵循 RED-GREEN-REFACTOR。

**步骤 1：RED - 编写失败的测试**

**调用 dev-tdd**：测试：

- 程序启动时会加载配置和 state
- 成功写入后才保存新 state
- 捕获异常后不崩溃，返回下一轮退避秒数

**步骤 2：验证 RED - 看着它失败**

**调用 dev-tdd**：运行：

```bash
pytest tests/eastmoney_kuaixun/test_main_loop.py -v
```

预期：FAIL。

**步骤 3：GREEN - 编写最小实现**

**调用 dev-tdd**：补齐 `main()` 与循环驱动：

- 加载 state
- 调用单轮执行函数
- 记录摘要日志
- `sleep` 下一轮

要求：

- 日志包含启动、增量数、写入数、退避秒数、错误摘要
- 不记录完整响应体

**步骤 4：验证 GREEN - 看着它通过**

**调用 dev-tdd**：运行：

```bash
pytest tests/eastmoney_kuaixun/test_main_loop.py -v
```

预期：PASS。

**步骤 5：REFACTOR（可选）**

**调用 dev-tdd**：抽出日志辅助函数，保持主循环清晰。

### 任务 8：补齐跨平台部署文件

**文件：**
- 创建：`/Users/moyueheng/.openclaw/workspace/deploy/macos/com.myhron.eastmoney-yw.plist`
- 创建：`/Users/moyueheng/.openclaw/workspace/deploy/windows/install-task.ps1`
- 创建：`/Users/moyueheng/.openclaw/workspace/deploy/windows/uninstall-task.ps1`
- 修改：`/Users/moyueheng/.openclaw/workspace/scripts/run-eastmoney-yw.sh`
- 修改：`/Users/moyueheng/.openclaw/workspace/scripts/run-eastmoney-yw.bat`

**步骤 1：编写 macOS `launchd` 配置**

创建 `.plist`，指向 `run-eastmoney-yw.sh`，并配置：

- `RunAtLoad`
- 异常退出自动重启
- stdout/stderr 到本地日志文件

**步骤 2：编写 Windows 安装脚本**

在 `install-task.ps1` 中创建计划任务，设置：

- 登录后启动
- 指向 `run-eastmoney-yw.bat`
- 任务名称固定
- 可重复安装/更新

**步骤 3：编写 Windows 卸载脚本**

在 `uninstall-task.ps1` 中删除同名任务。

**步骤 4：验证平台文件基本正确**

手工检查：

- macOS plist 语法可读
- PowerShell 脚本变量和路径引用正确

### 任务 9：补齐端到端集成测试样本

**文件：**
- 创建：`/Users/moyueheng/.openclaw/workspace/tests/fixtures/count_payload.json`
- 创建：`/Users/moyueheng/.openclaw/workspace/tests/fixtures/list_payload.json`
- 创建：`/Users/moyueheng/.openclaw/workspace/tests/eastmoney_kuaixun/test_integration_flow.py`

> **给 Kimi：** 此任务使用 `dev-tdd` skill。遵循 RED-GREEN-REFACTOR。

**步骤 1：RED - 编写失败的测试**

**调用 dev-tdd**：构造一个“第一次有 2 条新增、第二次无新增”的完整流程测试。

**步骤 2：验证 RED - 看着它失败**

**调用 dev-tdd**：运行：

```bash
pytest tests/eastmoney_kuaixun/test_integration_flow.py -v
```

预期：FAIL。

**步骤 3：GREEN - 编写最小实现**

**调用 dev-tdd**：通过 mock client / stub response 跑通：

- 读取样本
- 过滤新增
- 写 Markdown
- 更新 state

**步骤 4：验证 GREEN - 看着它通过**

**调用 dev-tdd**：运行：

```bash
pytest tests/eastmoney_kuaixun/test_integration_flow.py -v
```

预期：PASS。

**步骤 5：REFACTOR（可选）**

**调用 dev-tdd**：压缩重复样板，保持测试意图清晰。

### 任务 10：统一验证与文档补充

**文件：**
- 修改：`/Users/moyueheng/.openclaw/workspace/AGENTS.md`（仅在确有高信息密度通用知识需要补充时）
- 创建或修改：`/Users/moyueheng/.openclaw/workspace/README.md`

**步骤 1：运行完整测试**

运行：

```bash
pytest -v
```

预期：全部通过。

**步骤 2：手工验证 CLI**

运行：

```bash
uv run eastmoney-yw
```

预期：

- 正常启动
- 生成或读取 state
- 若有样本/真实数据，则写入 Markdown
- 输出简洁日志

**步骤 3：补充最小使用说明**

在 `README.md` 中写明：

- 如何用 `uv` 运行
- data/state/raw 目录含义
- 如何安装 macOS / Windows 后台任务
- 如何停止任务

**步骤 4：检查工作区知识文档**

运行：

```bash
find . -type f \( -name 'AGENTS.md' -o -name 'CLAUDE.md' \)
```

如果出现了值得长期保留的高密度通用知识，再最小化更新；若只是一次性实现细节，则不写入。

计划已完成后，按执行情况再决定是否提交。除非用户明确要求，否则不要自行提交 git commit。
