# 财经新闻分析系统

自动采集财经新闻、AI 分析并发送到飞书。

---

## 📋 准备工作（只需一次）

### 1. 确认已安装 Python 3.12+

打开命令提示符（CMD），输入：
```cmd
python --version
```

应该显示 `Python 3.12.x` 或更高版本。

如果没有安装，从这里下载：https://python.org/downloads

**安装时注意**：勾选 "Add Python to PATH"

---

### 2. 安装 uv（Python 包管理器）

打开 PowerShell，复制粘贴执行：
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

### 3. 安装 Kimi CLI

```cmd
pip install kimi-cli
```

---

### 4. 配置飞书（重要）

编辑项目根目录下的 `.env` 文件：

```bash
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**如何获取飞书配置：**

1. 登录 [飞书开发者平台](https://open.feishu.cn/app)
2. 创建企业自建应用
3. 开启权限：`im:chat:readonly`, `im:message:send_as_bot`
4. 发布应用并获取 App ID 和 Secret
5. 将应用添加到要发送的群聊

---

## 🚀 日常使用

### 启动系统

双击运行：`scripts/win/start.bat`

会看到：
- 两个黑色窗口弹出（新闻采集 + 新闻分析）
- 启动窗口提示"系统已启动"

**然后可以关掉启动窗口，服务会继续在后台运行。**

---

### 停止系统

双击运行：`scripts/win/stop.bat`

所有服务会停止，黑色窗口会关闭。

---

### 查看运行状态

查看日志文件：
```
input/data/state/news-analysis-loop.log
```

用记事本打开即可看到运行记录。

---

## ⚙️ 高级配置

### 修改分析频率

编辑 `start.bat`，找到这一行：
```bat
start "新闻分析" uv run python scripts/win/run_analysis.py
```

改为（例如改为 10 分钟）：
```bat
set SLEEP_SECONDS=600
start "新闻分析" uv run python scripts/win/run_analysis.py
```

---

### 修改飞书接收人

编辑 `.env` 文件中的：

```bash
# 发送到个人
FEISHU_USER_ALIAS_JSON={"用户名":"用户ID"}

# 发送到群聊  
FEISHU_CHAT_ALIAS_JSON={"群名称":"群ID"}
```

**获取 ID 的方法：**
- 用户 ID：飞书管理后台 → 组织架构 → 查看成员详情
- 群 ID：飞书开发者工具 → 调试 → 查看群信息

---

## 🔧 故障排查

### 双击 start.bat 闪退

1. 右键 `start.bat` → 编辑
2. 在文件开头添加 `pause`
3. 保存后再运行，看错误信息

### 提示 kimi 命令不存在

```cmd
pip install kimi-cli
```

### 提示 uv 命令不存在

重新执行 uv 安装命令（见上文第 2 步）。

### 日志显示发送失败

检查 `.env` 配置：
- App ID 和 Secret 是否正确
- 应用是否有消息发送权限
- 应用是否已加入目标群聊

---

## 📁 文件说明

```
wechat-claw/
├── scripts/win/
│   ├── start.bat          # 启动脚本
│   ├── stop.bat           # 停止脚本
│   └── run_analysis.py    # 分析服务（不要直接运行）
├── input/data/articles/   # 待分析的新闻
├── input/data/archived/   # 已分析的新闻归档
├── input/data/state/      # 日志和状态
└── .env                   # 飞书配置（需自己填写）
```

---

## 💡 使用流程总结

```
准备工作（一次）：
  安装 Python → 安装 uv → 安装 kimi-cli → 配置 .env

日常使用：
  双击 start.bat 启动
  ↓
  系统自动采集新闻、分析、发送到飞书
  ↓
  双击 stop.bat 停止
```

---

## 🤖 使用 Kimi CLI 解决问题

Kimi CLI 是一个 AI 编程助手，可以帮你解决使用中遇到的问题，或者修改代码实现新需求。

### 遇到问题怎么办？

**1. 直接问 Kimi**

在项目目录打开终端，执行：
```cmd
kimi
```

然后描述你的问题，例如：
- "start.bat 双击后闪退，怎么排查？"
- "日志显示发送失败，帮我看看"
- "想改成每小时分析一次，怎么改？"

**2. 让 Kimi 自动修复**

如果 Kimi 分析出代码有问题，可以让它直接修改：
```cmd
kimi --yolo "修复 start.bat 的编码问题"
```

### 想加新功能？

**描述你的需求，Kimi 帮你编程：**

```cmd
kimi "我想在发送报告前加一个确认步骤，帮我实现"
```

或

```cmd
kimi "分析频率改成可配置，不要写死在代码里"
```

Kimi 会：
1. 理解你的需求
2. 查看现有代码
3. 给出修改方案
4. 自动修改代码（加 `--yolo` 参数）

### 常用 Kimi 命令

| 命令 | 作用 |
|------|------|
| `kimi` | 进入交互模式，可以聊天提问 |
| `kimi "你的问题"` | 直接提问，回答后退出 |
| `kimi --yolo "任务"` | 自动执行，无需确认（适合简单修改） |
| `kimi -p "分析日志文件"` | 使用特定 prompt 文件 |

### 示例对话

**场景 1：排查问题**
```
> kimi
kimi> start.bat 双击后闪退，怎么排查？
AI: 先检查 Python 是否安装...
```

**场景 2：修改配置**
```
> kimi "把分析间隔改成 10 分钟"
AI: 我来修改 scripts/win/run_analysis.py...
[修改完成]
```

**场景 3：添加功能**
```
> kimi "想在发送前弹窗确认"
AI: 我需要在 send_message.py 中添加弹窗逻辑...
[修改完成]
```

---

有问题请检查日志：`input/data/state/news-analysis-loop.log`

或直接在项目目录运行 `kimi` 寻求帮助！
