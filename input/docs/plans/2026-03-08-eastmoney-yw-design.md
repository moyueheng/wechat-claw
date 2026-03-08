# 东方财富焦点快讯采集设计

**日期：** 2026-03-08

**目标：** 实时获取 `https://kuaixun.eastmoney.com/yw.html` 的焦点快讯，以较低风险的方式增量抓取，并将新内容持续保存到本地 Markdown；同时兼容 macOS 和 Windows 的后台运行。

## 已确认约束

- 数据源页面：`https://kuaixun.eastmoney.com/yw.html`
- 栏目：焦点，对应 `fastColumn=101`
- 本地保存格式：Markdown
- 运行方式：后台守护
- 平台要求：兼容 macOS 和 Windows
- 风控约束：不能机械高频轮询，必须有抖动和退避
- 工程约束：不引入新的重型框架，不做跨模块隐式耦合

## 事实依据

对页面和脚本的检查表明：

- 页面存在完整 HTML，不是纯前端空壳
- 页面脚本 `kuaixun.js` 会以大约 9 秒为节奏轮询接口
- `yw.html` 映射到栏目 `101`
- 增量接口核心为：
  - `getFastNewsCount?...&fastColumn=101`
  - `getFastNewsList?...&fastColumn=101`
- 页面自身使用 `realSort` 作为增量边界判断依据

因此，推荐直接使用接口做增量拉取，而不是反复解析整页 HTML，也不需要浏览器自动化常驻。

## 方案比较

### 方案 A：跨平台常驻进程 + 接口轮询 + Markdown 落盘

这是最终选定方案。

优点：

- 贴近源站现有刷新机制
- 资源占用低
- 比抓 HTML 或浏览器 DOM 更稳
- 业务逻辑天然可跨平台

缺点：

- 依赖接口字段结构
- 对方改接口后需要适配

### 方案 B：浏览器自动化常驻 + 读取 DOM

优点：

- 接近用户真实访问链路
- 若页面还能渲染，部分接口变化时可能仍可工作

缺点：

- 资源占用明显更高
- 长期稳定性差
- 不适合这个仅需增量文本抓取的需求

### 方案 C：定时短任务 + 接口增量抓取

优点：

- 实现简单
- 单次失败影响范围小

缺点：

- 不符合“后台守护”的目标语义
- 实时性和恢复速度不如常驻模型

## 最终设计

采用“一套跨平台 Python 常驻采集器 + 平台适配托管层”的结构：

```text
OS service manager
  |
  +-- macOS: launchd
  |
  +-- Windows: Task Scheduler
  |
  v
collector process
  |
  +-- 低频随机轮询 count 接口
  +-- 有增量时调用 list 接口
  +-- 基于 realSort 和本地窗口做去重
  +-- 将新快讯追加写入 Markdown
  +-- 维护本地 state
```

这里严格区分两层：

- 业务层：抓取、解析、去重、写文件、维护状态
- 托管层：让进程在不同系统上后台拉起和重启

这样可以保证跨平台时只替换启动方式，不分叉业务代码。

## 建议目录结构

```text
.
├── src/
│   └── eastmoney_kuaixun/
│       ├── __init__.py
│       ├── config.py
│       ├── models.py
│       ├── client.py
│       ├── writer.py
│       ├── state.py
│       └── daemon.py
├── tests/
│   └── eastmoney_kuaixun/
│       ├── test_client.py
│       ├── test_writer.py
│       ├── test_state.py
│       └── test_daemon.py
├── data/
│   ├── raw/
│   └── state/
├── scripts/
│   ├── run-eastmoney-yw.sh
│   └── run-eastmoney-yw.bat
└── deploy/
    ├── macos/
    │   └── com.myhron.eastmoney-yw.plist
    └── windows/
        ├── install-task.ps1
        └── uninstall-task.ps1
```

## 模块职责

### `config.py`

- 管理栏目 ID、轮询区间、退避上限、数据目录等配置
- 提供跨平台默认路径

### `models.py`

- 定义新闻记录、状态记录等数据结构
- 所有 Python 代码都应带完整类型注解

### `client.py`

- 负责访问东方财富接口
- 解析 `count` 和 `list` 响应
- 屏蔽请求细节和字段映射

### `state.py`

- 读取和写入本地状态文件
- 维护 `last_real_sort` 与 `recent_ids`

### `writer.py`

- 按月生成 Markdown 文件
- 负责日标题、条目格式和追加写入

### `daemon.py`

- 负责编排轮询循环
- 控制抖动、退避、异常恢复
- 串联 `client/state/writer`

## 数据流

```text
启动
  |
  +-- 读取 state
  |
  +-- 冷启动拉取最近一批，建立初始游标
  |
  +-- 进入循环
        |
        +-- count == 0
        |     -> 更新检查时间
        |     -> 进入下一轮等待
        |
        +-- count > 0
              |
              +-- 拉取最新列表
              +-- 筛选 realSort > last_real_sort 的新闻
              +-- recent_ids 二次去重
              +-- 成功写入 Markdown
              +-- 更新 state
```

## 去重规则

双层去重：

1. 主游标：`realSort > last_real_sort`
2. 保险窗口：维护最近 `500-2000` 条 seen key

优先 key：

```text
{code}:{realSort}
```

缺少 `code` 时退化为：

```text
{showTime}:{title}
```

**重要约束：** 只有在 Markdown 成功写入后，才允许推进 `last_real_sort` 和本地去重窗口，避免写文件失败导致数据丢失。

## Markdown 组织方式

按月归档：

```text
data/raw/eastmoney-yw-YYYY-MM.md
```

建议格式：

```md
# 东方财富焦点快讯归档

- 来源页: https://kuaixun.eastmoney.com/yw.html
- 栏目: 101 / 焦点
- 开始记录时间: 2026-03-08 11:30:00 +08:00

## 2026-03-08

### 11:31
标题或摘要正文

- code: 123456789
- real_sort: 1772939953000
- url: https://finance.eastmoney.com/a/123456789.html
```

落盘字段最少包含：

- `showTime`
- `title`
- `summary`
- `code`
- `realSort`
- 详情链接

展示时可优先使用：

```text
summary 存在 -> 展示 summary
否则 -> 展示 title
```

## 限流与风控策略

不使用页面的固定 9 秒轮询策略，改为更保守的低频常驻模型：

- 正常轮询：`30-90 秒` 随机抖动
- 连续多轮无增量：扩大到 `60-180 秒`
- 接口失败或疑似限流：指数退避到 `3/5/10/15 分钟`
- 恢复成功后：回到正常轮询

请求顺序严格最小化：

1. 先请求 `count`
2. 只有 `count > 0` 才请求 `list`
3. `list` 仅拉最近小批量数据
4. 不主动翻历史分页，不做站内全量回补

## 异常处理

异常分四类：

1. 网络异常
   - 超时、连接失败、DNS 问题
   - 处理：记录错误并短期退避

2. HTTP / 接口异常
   - 403、429、5xx、返回结构变化
   - 处理：提高退避级别并保留简短诊断信息

3. 数据异常
   - 单条字段缺失、时间为空、`realSort` 缺失
   - 处理：跳过单条，不让整轮失败

4. 本地写入异常
   - 目录不存在、文件不可写、磁盘异常
   - 处理：停止推进状态，避免“已消费未落盘”

## 后台托管

托管方案：

- macOS：`launchd`
- Windows：`Task Scheduler`

原则：

- 核心采集器是普通 CLI 常驻进程
- 平台差异只存在于部署脚本和托管配置
- 不在第一版引入原生 Windows Service

## 测试与验收

### 逻辑测试

- 解析 `count/list` 响应
- `realSort` 增量判断
- `recent_ids` 去重
- Markdown 渲染
- state 读写
- “写入成功后再推进游标”顺序

### 集成测试

- 首次运行能写入 Markdown
- 再次运行不会重复写入相同新闻
- `count=0` 时不写文件
- `list` 返回重叠数据时仍只写新增

### 平台验证

- macOS 能由 `launchd` 拉起
- Windows 能由 `Task Scheduler` 拉起
- 两个平台输出格式一致
- 两个平台状态文件格式一致

### 完成标准

1. 手动运行 CLI 能增量抓取并写入 Markdown
2. 重复运行不重复写同一批新闻
3. macOS 可后台运行
4. Windows 可后台运行
5. 具备抖动、退避、失败保护
6. state 与 Markdown 落盘顺序正确，不丢数据
7. 具备覆盖核心逻辑的自动化测试
