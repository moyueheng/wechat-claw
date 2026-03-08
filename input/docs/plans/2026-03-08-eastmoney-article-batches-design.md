# 东方财富焦点快讯正文批次归档设计

**日期：** 2026-03-08

**目标：** 在现有东方财富焦点快讯增量采集器基础上，继续保留月度 Markdown 归档，同时新增正文抓取能力，并按每 5 条新闻正文一个批次目录的方式落盘。

## 已确认约束

- 数据源列表页：`https://kuaixun.eastmoney.com/yw.html`
- 列表抓取仍然基于现有 `fastColumn=101` 接口
- 详情页正文来自列表项中的详情链接
- 保留现有月度 Markdown 输出
- 新增正文输出目录：`data/articles/`
- 批次目录结构固定为：`data/articles/YYYY-MM-DD/YYYYMMDD-HHMMSS_0001/`
- 每个批次目录固定 5 条新闻正文
- 批次编号按实际成功落盘顺序递增
- 不引入新的重型框架
- 禁止跨模块隐式耦合

## 事实依据

对当前仓库与线上页面的检查表明：

- 当前实现已能通过 `getFastNewsList` 获取列表项，列表项已包含 `url`
- 当前 `url` 可直接访问东方财富正文页，例如：
  - `https://finance.eastmoney.com/a/202603083665282988.html`
- 当前正文页 HTML 中：
  - 正文主体位于 `id="ContentBody"`
  - 作者位于正文头部信息区
  - 来源位于正文头部与正文尾部均可提取
- 现有项目中：
  - `client.py` 负责列表接口访问
  - `daemon.py` 负责编排单轮采集与主循环
  - `writer.py` 负责月度 Markdown 写入
  - `state.py` 仅维护 `last_real_sort` 与 `recent_ids`

因此，正文抓取最合适的方式是在现有增量链路后追加详情页抓取与批次写盘，而不是额外起一套补抓进程。

## 方案比较

### 方案 A：在现有采集链路后追加正文抓取与批次写盘

这是最终选定方案。

优点：

- 与现有模块边界一致
- 复用现有增量去重与状态推进机制
- 不需要二次扫描 Markdown 或额外补偿任务
- 易于保证“正文未成功则不推进游标”的一致性

缺点：

- 状态模型会比现在更复杂
- 单轮采集中需要额外访问详情页，延迟会增加

### 方案 B：将正文直接内联写入现有月度 Markdown

优点：

- 实现最简单

缺点：

- 不满足“每个文件夹五条正文”的明确输出要求

### 方案 C：单独实现一套正文补抓器

优点：

- 与现有主采集器解耦

缺点：

- 状态分裂
- 容易出现列表与正文不一致
- 需要重复扫描已有产物，增加维护成本

## 最终设计

采用“列表增量采集 + 详情页正文提取 + 两套写盘器”的结构：

```text
list API
  |
  +-- 解析列表项
  |
  +-- 过滤新增项
  |
  +-- 逐条抓取详情页正文
  |
  +-- 写入月度 Markdown
  |
  +-- 累积到正文批次缓冲
  |
  +-- 满 5 条时写入一个批次目录
  |
  +-- 成功后推进 state
```

模块分层保持显式：

- `client.py`：列表接口与详情页正文抓取
- `models.py`：列表项、正文项、正文批次状态模型
- `writer.py`：月度 Markdown 写入
- 新增正文批次写盘模块：只负责 `data/articles/` 输出
- `state.py`：统一持久化游标、去重窗口、正文批次缓冲状态
- `daemon.py`：编排抓取、失败处理、状态推进

## 目录结构

新增输出目录结构如下：

```text
data/
├── raw/
│   └── eastmoney-yw-2026-03.md
├── articles/
│   ├── 2026-03-08/
│   │   ├── 20260308-083703_0001/
│   │   │   ├── 01-202603083665282988.md
│   │   │   ├── 02-202603073665178976.md
│   │   │   ├── 03-...
│   │   │   ├── 04-...
│   │   │   └── 05-...
│   │   └── 20260308-121122_0002/
│   └── 2026-03-09/
└── state/
    └── eastmoney-yw-state.json
```

规则：

- 第一层目录：新闻批次锚点时间所在日期，格式 `YYYY-MM-DD`
- 第二层目录：`{batch_anchor_time}_{batch_index:04d}`
- `batch_anchor_time` 取该批第一条正文的 `show_time`，格式化为 `YYYYMMDD-HHMMSS`
- `batch_index` 为全局递增编号，按正文成功落盘顺序生成
- 单篇正文文件命名：`{position:02d}-{code_or_fallback}.md`

## 数据模型

建议在现有模型基础上新增两个显式模型：

```text
FastNewsItem
  -> 列表接口返回的单条快讯

ArticleDetail
  -> 正文页提取后的结构化结果

PendingArticleBatchItem
  -> 已抓取正文但尚未凑满 5 条、暂存在 state 中的条目
```

`ArticleDetail` 最少包含：

- `code`
- `title`
- `summary`
- `show_time`
- `real_sort`
- `url`
- `author`
- `source`
- `content_text`

`CollectorState` 需要新增：

- `article_batch_index`
- `article_pending_items`

其中 `article_pending_items` 必须持久化正文内容本身，不能只存 `code` 或 `url`，否则进程重启后会丢失半批正文。

## 数据流

一次成功采集流程如下：

```text
读取 state
  |
  +-- 调用 count/list 接口获取最新列表
  |
  +-- 基于 last_real_sort + recent_ids 过滤新增项
  |
  +-- 逐条抓取详情页并提取正文
  |
  +-- 将新增项追加到月度 Markdown
  |
  +-- 将正文项追加到 article_pending_items
  |
  +-- 当 pending >= 5 时：
        |
        +-- 取前 5 条组成一个批次
        +-- 创建批次目录
        +-- 写入 5 个正文文件
        +-- article_batch_index += 1
        +-- 从 pending 中移除这 5 条
  |
  +-- 保存新 state
```

这里的关键一致性约束是：

- 只有在“月度 Markdown 写成功 + 正文批次写成功 + state 写成功”后，才推进 `last_real_sort`
- 详情页正文抓取失败时，该条新闻视为未完成，不推进游标
- `pending` 不满 5 条时不生成目录，只写入 state 等待下轮凑满

## 正文提取策略

正文提取保持轻量，不引入重型依赖。

提取顺序建议如下：

1. 读取详情页 HTML
2. 提取 `id="ContentBody"` 内的正文片段
3. 将段落 HTML 转换为纯文本段落
4. 去掉以下非正文内容：
   - 广告图片
   - 举报、责任编辑
   - 声明性尾注
   - 与正文无关的分享、评论区域
5. 额外提取作者与来源

失败策略：

- 未找到 `ContentBody` 视为正文抓取失败
- 不用 `summary` 冒充正文
- 失败条目不推进游标

## 输出格式

### 月度 Markdown

现有月度 Markdown 保持继续输出，仍用于总归档与快速浏览。

可选地增加一行指向正文文件夹或正文文件的引用，但不是本次设计的硬要求。

### 单篇正文文件

建议格式：

```md
# 新闻标题

- show_time: 2026-03-08 08:37:03
- code: 202603083665282988
- url: https://finance.eastmoney.com/a/202603083665282988.html
- author: 宋亚芬
- source: 中新经纬
- real_sort: 1772939953000
- batch: 20260308-083703_0001
- position: 01

## 正文

正文第一段

正文第二段
```

这样既便于人读，也便于后续脚本处理。

## 错误处理

需要覆盖以下失败场景：

- 列表接口成功，但详情页请求超时
- 详情页返回 HTML，但正文节点缺失
- 月度 Markdown 写入成功，但正文批次目录写入失败
- 正文批次目录写入成功，但 state 保存失败

原则：

- 失败时不推进 `last_real_sort`
- 已写入磁盘的正文批次必须通过显式命名与 state 协调避免重复编号
- 状态写入继续使用原子替换

## 测试策略

需要新增或扩展以下测试：

- `test_client.py`
  - 详情页 HTML 正文提取
  - 作者/来源提取
  - 正文缺失时返回失败
- `test_state.py`
  - `article_batch_index` 与 `article_pending_items` 的序列化与反序列化
- 新增正文批次 writer 测试
  - 满 5 条才创建目录
  - 目录命名与文件命名正确
  - 同一批写出 5 个正文文件
- `test_integration_flow.py`
  - 首轮 2 条正文进入 pending，不落批次目录
  - 后续补足 5 条后生成 `_0001`
  - 下一批继续生成 `_0002`
  - 正文失败不推进 `last_real_sort`

## 不做的事

本次明确不做：

- 额外起一套正文补抓进程
- 引入浏览器自动化常驻抓取
- 引入重型 HTML 解析框架
- 将正文目录再按年份拆一级大目录
- 用 `summary` 代替正文

## 结论

推荐方案是在现有增量采集链路中追加详情页正文抓取，并用显式的正文批次状态来驱动 `data/articles/YYYY-MM-DD/YYYYMMDD-HHMMSS_0001/` 这种目录输出。这样既保留现有月度 Markdown，又能稳定满足“每 5 条正文一个文件夹、按时间顺序编号”的需求，同时避免跨模块隐式耦合。
