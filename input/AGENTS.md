# 仓库指南

## 项目概览

这个仓库是一个基于 Python 的东方财富焦点快讯采集器，目标站点为 `https://kuaixun.eastmoney.com/yw.html`。

核心能力：

- 增量抓取焦点快讯列表
- 抓取每条新闻详情页正文
- 将快讯按月写入 `data/raw/` 下的 Markdown
- 将正文按天与批次写入 `data/articles/`
- 用 `data/state/` 持久化采集状态

## 目录结构

- `src/eastmoney_kuaixun/`：应用代码
- `tests/eastmoney_kuaixun/`：单元测试与集成测试
- `tests/fixtures/`：测试夹具，包括列表接口样本和详情页 HTML
- `scripts/`：跨平台启动脚本
- `deploy/macos/`：macOS `launchd` 配置
- `deploy/windows/`：Windows 计划任务脚本
- `docs/plans/`：设计文档与实施计划
- `data/raw/`、`data/articles/`、`data/state/`：运行时输出，不要提交

业务逻辑必须放在 `src/eastmoney_kuaixun/` 内，不要把部署脚本和采集器内部实现耦合在一起。

## 运行方式

运行要求：

- Python `>=3.12`
- `uv`

常用命令：

- `uv run eastmoney-yw`：执行单轮增量采集
- `uv run eastmoney-yw --force-refresh`：忽略当前 state 一次，强制抓取最新列表并追加写入
- `uv run eastmoney-yw --daemon`：以前台常驻模式运行
- `uv run eastmoney-yw --data-dir /path/to/data`：指定自定义数据目录
- `uv run --extra dev pytest -v`：运行完整测试套件
- `uv run --extra dev pytest tests/eastmoney_kuaixun/test_daemon.py -v`：运行单个测试文件

统一使用 `uv` 做依赖管理和执行，不要随意引入额外本地工作流。

## 输出规则

运行时输出目录：

- `data/raw/`：按月归档的 Markdown 快讯文件
- `data/articles/`：按天和批次归档的正文文件
- `data/state/`：状态文件和后台日志

正文目录规则：

- 正文抓取成功后立即写入当前批次目录
- 正文输出目录格式为 `data/articles/YYYY-MM-DD/YYYYMMDD-HHMMSS_0001/`
- 新闻日期变化时，强制切到新的日期目录和新批次
- 单个批次目录最多 5 条正文
- 当前目录写满 5 条后，下一条新闻创建新目录
- 月度 Markdown 中会写入 `article_file` 相对路径索引，指向对应正文文件

`--force-refresh` 说明：

- 该参数只忽略当前 state 一次
- 会重新抓取最新列表并追加写入
- 可能在月度 Markdown 和正文目录中产生重复条目
- 适合手动补抓、验证正文落盘或重建默认数据目录

## 模块职责

- `config.py`：配置与数据目录路径
- `models.py`：数据模型与状态模型
- `client.py`：列表接口访问与详情页正文提取
- `writer.py`：月度 Markdown 写入
- `article_writer.py`：正文批次目录与正文文件写入
- `state.py`：状态文件读写
- `daemon.py`：轮询编排、批次切换、状态推进、CLI 入口

## 编码规范

- 目标 Python 版本为 `>=3.12`
- 使用 4 空格缩进
- 所有函数、方法、数据结构都必须有显式类型注解
- 函数、变量、测试名使用 `snake_case`
- 数据类使用 `PascalCase`
- 优先保持模块小而清晰，避免一个文件承担多个职责
- 标准库优先，只有在确有必要时才引入轻量依赖

## 测试要求

- 测试框架使用 `pytest`
- 测试文件命名为 `test_*.py`
- 行为变更前先补回归测试
- 接口解析优先使用夹具驱动测试
- 修改轮询、状态推进、正文落盘逻辑时，必须同时覆盖单元测试和端到端流转测试
- 对外宣称完成前必须运行完整测试：`uv run --extra dev pytest -v`

## 提交规范

遵循 Conventional Commits：

- `feat: ...`
- `fix: ...`
- `docs: ...`

要求：

- 每个 commit 只做一件事
- 提交信息必须可读、可回滚、可 bisect
- 作者信息仅允许：`myhron <moyueheng@gmail.com>`

## 安全与运行注意事项

- 不要提交 `data/` 下的运行产物
- 不要提交本地虚拟环境、截图或临时产物
- 启用 macOS `launchd` 或 Windows 计划任务前，先确认路径配置正确
- 只有在 Markdown、正文写盘和 state 都成功后，才允许推进增量游标
