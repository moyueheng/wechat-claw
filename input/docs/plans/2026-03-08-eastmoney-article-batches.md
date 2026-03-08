# EastMoney Article Batches Implementation Plan

> **给 Kimi：** 必需子 skill：使用 `dev-executing-plans` 逐个任务实施此计划。

**目标：** 在现有东方财富焦点快讯采集器上新增详情页正文抓取能力，并将正文按每 5 条一个批次目录写入 `data/articles/YYYY-MM-DD/YYYYMMDD-HHMMSS_0001/`，同时继续保留现有月度 Markdown 输出。

**架构：** 继续沿用现有“列表抓取 -> 过滤新增 -> Markdown 落盘 -> state 推进”的主链路，在 `client.py` 中新增详情页提取，在 state 中新增正文批次缓冲，在独立正文 writer 中负责批次目录输出。游标推进仍由 `daemon.py` 统一控制，确保正文抓取失败时不推进 `last_real_sort`。

**技术栈：** Python 3.12、标准库 `urllib/json/pathlib/html.parser/dataclasses`、`pytest`、现有 `uv` 工作流。

---

### 任务 1：补充设计文档与夹具

**文件：**
- 已创建：`/Users/moyueheng/.openclaw/workspace/input/docs/plans/2026-03-08-eastmoney-article-batches-design.md`
- 创建：`/Users/moyueheng/.openclaw/workspace/input/tests/fixtures/detail_page.html`
- 修改：`/Users/moyueheng/.openclaw/workspace/input/README.md`

**步骤 1：保存一个真实详情页 HTML 夹具**

运行：

```bash
curl -L --max-time 20 'https://finance.eastmoney.com/a/202603083665282988.html' -o tests/fixtures/detail_page.html
```

预期：生成 `tests/fixtures/detail_page.html`，后续解析测试不依赖外网。

**步骤 2：在 README 中补充正文目录说明**

说明：

- 新增 `data/articles/` 的用途
- 批次目录 5 条一组
- 月度 Markdown 与正文目录并存

**步骤 3：验证文档与夹具存在**

运行：

```bash
test -f tests/fixtures/detail_page.html && test -f docs/plans/2026-03-08-eastmoney-article-batches-design.md
```

预期：退出码为 0。

### 任务 2：扩展数据模型与状态模型

**文件：**
- 修改：`/Users/moyueheng/.openclaw/workspace/input/src/eastmoney_kuaixun/models.py`
- 修改：`/Users/moyueheng/.openclaw/workspace/input/tests/eastmoney_kuaixun/test_models.py`

> **给 Kimi：** 此任务使用 `dev-tdd` skill。遵循 RED-GREEN-REFACTOR。

**步骤 1：RED - 编写失败的测试**

**调用 dev-tdd**：在 `tests/eastmoney_kuaixun/test_models.py` 中新增完整测试，覆盖：

```python
from eastmoney_kuaixun.models import (
    ArticleDetail,
    CollectorState,
    PendingArticleBatchItem,
)


def test_pending_article_batch_item_preserves_article_fields() -> None:
    item = PendingArticleBatchItem(
        code="202603083665282988",
        title="标题",
        summary="摘要",
        show_time="2026-03-08 08:37:03",
        real_sort="100",
        url="https://finance.eastmoney.com/a/202603083665282988.html",
        author="作者",
        source="来源",
        content_text="正文",
    )
    assert item.code == "202603083665282988"
    assert item.content_text == "正文"


def test_collector_state_tracks_article_batch_progress() -> None:
    state = CollectorState(
        last_real_sort="101",
        recent_ids=["a"],
        article_batch_index=2,
        article_pending_items=[
            PendingArticleBatchItem(
                code="1",
                title="t",
                summary="s",
                show_time="2026-03-08 08:37:03",
                real_sort="101",
                url="u",
                author="a",
                source="src",
                content_text="body",
            )
        ],
    )
    assert state.article_batch_index == 2
    assert len(state.article_pending_items) == 1
```

**步骤 2：验证 RED - 看着它失败**

**调用 dev-tdd**：运行：

```bash
uv run --extra dev pytest tests/eastmoney_kuaixun/test_models.py -v
```

预期：FAIL，原因是新模型或字段不存在。

**步骤 3：GREEN - 编写最小实现**

**调用 dev-tdd**：在 `models.py` 中新增：

- `ArticleDetail`
- `PendingArticleBatchItem`
- `CollectorState.article_batch_index`
- `CollectorState.article_pending_items`

要求：

- 所有字段完整类型注解
- 保持现有 `FastNewsItem` 行为不变
- 如有必要，添加从 `ArticleDetail` 到 `PendingArticleBatchItem` 的显式转换辅助方法

**步骤 4：验证 GREEN - 看着它通过**

**调用 dev-tdd**：运行：

```bash
uv run --extra dev pytest tests/eastmoney_kuaixun/test_models.py -v
```

预期：PASS。

**步骤 5：REFACTOR（可选）**

**调用 dev-tdd**：消除重复字段构造，保持模型层不混入网络解析逻辑。

### 任务 3：扩展 state 持久化，支持正文批次缓冲

**文件：**
- 修改：`/Users/moyueheng/.openclaw/workspace/input/src/eastmoney_kuaixun/state.py`
- 修改：`/Users/moyueheng/.openclaw/workspace/input/tests/eastmoney_kuaixun/test_state.py`

> **给 Kimi：** 此任务使用 `dev-tdd` skill。遵循 RED-GREEN-REFACTOR。

**步骤 1：RED - 编写失败的测试**

**调用 dev-tdd**：在 `tests/eastmoney_kuaixun/test_state.py` 中新增完整测试，覆盖：

```python
from pathlib import Path

from eastmoney_kuaixun.models import CollectorState, PendingArticleBatchItem
from eastmoney_kuaixun.state import load_state, save_state


def test_save_and_load_state_round_trip_with_article_pending_items(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    state = CollectorState(
        last_real_sort="12",
        recent_ids=["x"],
        article_batch_index=3,
        article_pending_items=[
            PendingArticleBatchItem(
                code="1",
                title="t",
                summary="s",
                show_time="2026-03-08 08:37:03",
                real_sort="12",
                url="u",
                author="a",
                source="src",
                content_text="body",
            )
        ],
    )
    save_state(path, state)
    loaded = load_state(path)
    assert loaded.article_batch_index == 3
    assert loaded.article_pending_items[0].content_text == "body"
```

**步骤 2：验证 RED - 看着它失败**

**调用 dev-tdd**：运行：

```bash
uv run --extra dev pytest tests/eastmoney_kuaixun/test_state.py -v
```

预期：FAIL，原因是 state 尚未序列化/反序列化新增字段。

**步骤 3：GREEN - 编写最小实现**

**调用 dev-tdd**：在 `state.py` 中：

- 为 `CollectorState` 新字段做 JSON 序列化与反序列化
- 保持 state 缺失旧字段时可向后兼容
- 继续沿用原子写入策略

**步骤 4：验证 GREEN - 看着它通过**

**调用 dev-tdd**：运行：

```bash
uv run --extra dev pytest tests/eastmoney_kuaixun/test_state.py -v
```

预期：PASS。

**步骤 5：REFACTOR（可选）**

**调用 dev-tdd**：将 pending item 的序列化逻辑提取成小函数，避免 `save_state` 过长。

### 任务 4：在 client 中实现详情页正文提取

**文件：**
- 修改：`/Users/moyueheng/.openclaw/workspace/input/src/eastmoney_kuaixun/client.py`
- 修改：`/Users/moyueheng/.openclaw/workspace/input/tests/eastmoney_kuaixun/test_client.py`
- 使用：`/Users/moyueheng/.openclaw/workspace/input/tests/fixtures/detail_page.html`

> **给 Kimi：** 此任务使用 `dev-tdd` skill。遵循 RED-GREEN-REFACTOR。

**步骤 1：RED - 编写失败的测试**

**调用 dev-tdd**：在 `tests/eastmoney_kuaixun/test_client.py` 中新增完整测试，至少覆盖：

```python
from pathlib import Path

from eastmoney_kuaixun.client import parse_detail_html


def test_parse_detail_html_extracts_content_author_and_source() -> None:
    html = Path("tests/fixtures/detail_page.html").read_text(encoding="utf-8")
    detail = parse_detail_html(
        html=html,
        code="202603083665282988",
        title="AI终于学会自己干活了！大厂纷纷布局OpenClaw",
        summary="摘要",
        show_time="2026-03-08 08:37:03",
        real_sort="100",
        url="https://finance.eastmoney.com/a/202603083665282988.html",
    )
    assert "养虾人" in detail.content_text
    assert detail.author == "宋亚芬"
    assert detail.source == "中新经纬"


def test_parse_detail_html_raises_when_content_body_missing() -> None:
    html = "<html><body><div>empty</div></body></html>"
    try:
        parse_detail_html(
            html=html,
            code="1",
            title="t",
            summary="s",
            show_time="2026-03-08 08:37:03",
            real_sort="100",
            url="u",
        )
    except ValueError as exc:
        assert "ContentBody" in str(exc)
    else:
        raise AssertionError("expected ValueError")
```

**步骤 2：验证 RED - 看着它失败**

**调用 dev-tdd**：运行：

```bash
uv run --extra dev pytest tests/eastmoney_kuaixun/test_client.py -v
```

预期：FAIL，原因是详情页解析函数尚不存在。

**步骤 3：GREEN - 编写最小实现**

**调用 dev-tdd**：在 `client.py` 中实现：

- `parse_detail_html(...) -> ArticleDetail`
- 详情页正文 HTML 提取
- 作者、来源提取
- `EastMoneyClient.fetch_article_detail(item: FastNewsItem) -> ArticleDetail`

要求：

- 优先使用标准库完成 HTML 提取
- 保留段落换行
- 过滤图片、广告、无关尾注
- 不用 `summary` 冒充正文

**步骤 4：验证 GREEN - 看着它通过**

**调用 dev-tdd**：运行：

```bash
uv run --extra dev pytest tests/eastmoney_kuaixun/test_client.py -v
```

预期：PASS。

**步骤 5：REFACTOR（可选）**

**调用 dev-tdd**：将 HTML 文本清洗拆成小函数，避免 `parse_detail_html` 过长。

### 任务 5：新增正文批次 writer

**文件：**
- 创建：`/Users/moyueheng/.openclaw/workspace/input/src/eastmoney_kuaixun/article_writer.py`
- 创建：`/Users/moyueheng/.openclaw/workspace/input/tests/eastmoney_kuaixun/test_article_writer.py`
- 修改：`/Users/moyueheng/.openclaw/workspace/input/src/eastmoney_kuaixun/config.py`

> **给 Kimi：** 此任务使用 `dev-tdd` skill。遵循 RED-GREEN-REFACTOR。

**步骤 1：RED - 编写失败的测试**

**调用 dev-tdd**：新增完整测试，覆盖：

```python
from pathlib import Path

from eastmoney_kuaixun.article_writer import (
    build_article_batch_dir_name,
    write_article_batch,
)
from eastmoney_kuaixun.models import PendingArticleBatchItem


def test_build_article_batch_dir_name_uses_anchor_time_and_index() -> None:
    item = PendingArticleBatchItem(
        code="202603083665282988",
        title="标题",
        summary="摘要",
        show_time="2026-03-08 08:37:03",
        real_sort="100",
        url="u",
        author="a",
        source="src",
        content_text="body",
    )
    assert build_article_batch_dir_name(item, 1) == "20260308-083703_0001"


def test_write_article_batch_writes_five_article_files(tmp_path: Path) -> None:
    items = []
    for index in range(5):
        items.append(
            PendingArticleBatchItem(
                code=str(index + 1),
                title=f"title-{index + 1}",
                summary="summary",
                show_time=f"2026-03-08 08:37:0{index + 1}",
                real_sort=str(100 + index),
                url=f"https://example.com/{index + 1}",
                author="a",
                source="src",
                content_text=f"body-{index + 1}",
            )
        )
    output_dir = write_article_batch(tmp_path, items, batch_index=1)
    assert output_dir.name == "20260308-083701_0001"
    assert len(list(output_dir.glob('*.md'))) == 5
```

**步骤 2：验证 RED - 看着它失败**

**调用 dev-tdd**：运行：

```bash
uv run --extra dev pytest tests/eastmoney_kuaixun/test_article_writer.py -v
```

预期：FAIL，原因是新模块与函数尚不存在。

**步骤 3：GREEN - 编写最小实现**

**调用 dev-tdd**：在 `article_writer.py` 中实现：

- `build_article_day_dir(...)`
- `build_article_batch_dir_name(...)`
- `build_article_file_name(...)`
- `render_article_markdown(...)`
- `write_article_batch(...)`

并在 `config.py` 中新增：

- `articles_dir`

要求：

- 只接受恰好 5 条正文项写一个批次
- 自动创建 `data/articles/YYYY-MM-DD/` 目录
- 文件内容包含元数据和正文

**步骤 4：验证 GREEN - 看着它通过**

**调用 dev-tdd**：运行：

```bash
uv run --extra dev pytest tests/eastmoney_kuaixun/test_article_writer.py -v
```

预期：PASS。

**步骤 5：REFACTOR（可选）**

**调用 dev-tdd**：提取时间格式化和文件命名辅助函数，减少重复。

### 任务 6：在 daemon 中接入正文抓取与批次缓冲

**文件：**
- 修改：`/Users/moyueheng/.openclaw/workspace/input/src/eastmoney_kuaixun/daemon.py`
- 修改：`/Users/moyueheng/.openclaw/workspace/input/tests/eastmoney_kuaixun/test_daemon.py`
- 修改：`/Users/moyueheng/.openclaw/workspace/input/tests/eastmoney_kuaixun/test_integration_flow.py`

> **给 Kimi：** 此任务使用 `dev-tdd` skill。遵循 RED-GREEN-REFACTOR。

**步骤 1：RED - 编写失败的测试**

**调用 dev-tdd**：扩展 `test_daemon.py` 与 `test_integration_flow.py`，至少覆盖：

```python
from pathlib import Path

from eastmoney_kuaixun.config import load_settings
from eastmoney_kuaixun.daemon import run_collection_cycle
from eastmoney_kuaixun.models import CollectorState


class DetailFixtureClient:
    def __init__(self, items, details) -> None:
        self._items = items
        self._details = details

    def fetch_increment_count(self, sort_start: str) -> int:
        return len(self._items)

    def fetch_latest_items(self, sort_end: str):
        return self._items

    def fetch_article_detail(self, item):
        return self._details[item.code]


def test_run_collection_cycle_keeps_pending_articles_until_five(tmp_path: Path) -> None:
    settings = load_settings(tmp_path)
    client = DetailFixtureClient(items=[...2 items...], details={...})
    result = run_collection_cycle(
        client=client,
        settings=settings,
        state=CollectorState(),
        empty_rounds=0,
        failure_count=0,
    )
    assert result.written == 2
    assert len(result.state.article_pending_items) == 2
    assert not settings.articles_dir.exists()
```

再补一个完整测试，验证第 5 条到来时：

- 生成 `_0001`
- 目录里有 5 个文件
- `article_batch_index == 1`
- `article_pending_items == []`

以及一个失败测试，验证：

- 某条正文抓取异常时，本轮返回异常
- 调用方不会保存新 state

**步骤 2：验证 RED - 看着它失败**

**调用 dev-tdd**：运行：

```bash
uv run --extra dev pytest tests/eastmoney_kuaixun/test_daemon.py tests/eastmoney_kuaixun/test_integration_flow.py -v
```

预期：FAIL，原因是主循环尚未接入正文缓冲与批次写盘。

**步骤 3：GREEN - 编写最小实现**

**调用 dev-tdd**：在 `daemon.py` 中：

- 过滤新增列表项后，逐条调用 `fetch_article_detail`
- 继续写月度 Markdown
- 将正文项并入 `state.article_pending_items`
- 当 `pending >= 5` 时循环写批次目录
- 更新 `article_batch_index`
- 仅在全部成功后返回新 state

要求：

- 不改变现有轮询、退避、日志输出主结构
- 不在 writer 与 client 之间做隐式跨层调用
- 保持 `run_main_loop` 仍由外层决定何时 `save_state`

**步骤 4：验证 GREEN - 看着它通过**

**调用 dev-tdd**：运行：

```bash
uv run --extra dev pytest tests/eastmoney_kuaixun/test_daemon.py tests/eastmoney_kuaixun/test_integration_flow.py -v
```

预期：PASS。

**步骤 5：REFACTOR（可选）**

**调用 dev-tdd**：将“累积 pending 并切批”的逻辑提取为小函数，减少 `run_collection_cycle` 的分支复杂度。

### 任务 7：补充 writer 与 README 的联动说明

**文件：**
- 修改：`/Users/moyueheng/.openclaw/workspace/input/src/eastmoney_kuaixun/writer.py`
- 修改：`/Users/moyueheng/.openclaw/workspace/input/tests/eastmoney_kuaixun/test_writer.py`
- 修改：`/Users/moyueheng/.openclaw/workspace/input/README.md`

> **给 Kimi：** 此任务使用 `dev-tdd` skill。遵循 RED-GREEN-REFACTOR。

**步骤 1：RED - 编写失败的测试**

**调用 dev-tdd**：仅在你决定给月度 Markdown 增加正文目录引用时，新增测试，例如：

```python
from pathlib import Path

from eastmoney_kuaixun.models import FastNewsItem
from eastmoney_kuaixun.writer import render_item


def test_render_item_can_include_article_batch_hint() -> None:
    item = FastNewsItem(
        code="123",
        title="title",
        summary="summary",
        show_time="2026-03-08 11:31:00",
        real_sort="100",
        url="https://finance.eastmoney.com/a/123.html",
    )
    rendered = render_item(item)
    assert "url:" in rendered
```

如果本任务最终决定不修改月度 Markdown 格式，则只更新 README，不新增代码测试。

**步骤 2：验证 RED - 看着它失败**

**调用 dev-tdd**：仅在修改 `writer.py` 时运行相关测试：

```bash
uv run --extra dev pytest tests/eastmoney_kuaixun/test_writer.py -v
```

**步骤 3：GREEN - 编写最小实现**

**调用 dev-tdd**：如果需要，最小化调整 `writer.py`；否则只更新 README 说明：

- 月度 Markdown 仍是总归档
- `data/articles/` 保存正文批次目录

**步骤 4：验证 GREEN - 看着它通过**

**调用 dev-tdd**：运行相关测试或跳过并记录“本任务仅文档修改，无代码测试”。

### 任务 8：全量验证

**文件：**
- 验证：`/Users/moyueheng/.openclaw/workspace/input/tests/eastmoney_kuaixun/`

> **给 Kimi：** 此任务使用 `dev-verification` skill。在声称完成前必须运行验证命令并检查输出。

**步骤 1：运行完整测试套件**

运行：

```bash
uv run --extra dev pytest -v
```

预期：

- 全部 PASS
- 不出现新增的 flaky 失败

**步骤 2：运行一次本地单轮采集**

运行：

```bash
uv run eastmoney-yw --data-dir /tmp/eastmoney-article-batches
```

预期：

- 程序退出码为 0
- `/tmp/eastmoney-article-batches/raw/` 生成月度 Markdown
- 若本轮正文累积不足 5 条，则 state 中存在 `article_pending_items`
- 若本轮正文达到 5 条或以上，则 `/tmp/eastmoney-article-batches/articles/` 下出现批次目录

**步骤 3：人工检查目录结构**

运行：

```bash
find /tmp/eastmoney-article-batches -maxdepth 4 -type f | sort
```

预期：可看到月度 Markdown、state 文件，以及符合命名规则的正文批次文件。

### 任务 9：收尾文档同步

**文件：**
- 检查并按需修改：`/Users/moyueheng/.openclaw/workspace/input/AGENTS.md`

**步骤 1：核对仓库级知识是否需要更新**

检查：

- 是否需要在仓库结构中补充 `data/articles/`
- 是否需要在运行说明中补充正文批次输出

**步骤 2：如果有高信息密度变化，则更新 AGENTS.md**

要求：

- 只记录长期有效的结构与架构知识
- 不记录临时日志

**步骤 3：验证**

运行：

```bash
find . -type f \( -name 'AGENTS.md' -o -name 'CLAUDE.md' \) | sort
```

预期：已检查完所有相关代理说明文件。
