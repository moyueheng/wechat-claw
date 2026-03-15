"""
新闻分析服务 - Windows 版
定时扫描新闻并分析发送
"""
import os
import sys
import time
import subprocess
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
LOG_DIR = PROJECT_ROOT / "input" / "data" / "state"
LOG_FILE = LOG_DIR / "news-analysis-loop.log"
PID_FILE = LOG_DIR / "news-analysis-loop.pid"

# 默认配置
SLEEP_SECONDS = int(os.environ.get("SLEEP_SECONDS", "1800"))  # 30分钟
INITIAL_DELAY_SECONDS = int(os.environ.get("INITIAL_DELAY_SECONDS", "0"))

PROMPT = """使用这个 skill `.agents/skills/news-analysis/SKILL.md`。
最终分析报告只发送到飞书
如果 `.env` 中存在可用的飞书别名映射，则优先使用该映射解析发送目标。
如果没有可用的飞书目标配置，直接报错并结束
如果没有新增新闻就不要发送任何消息，直接结束任务。
按时间顺序处理全部待分析新闻，并在每条发送完成后按 skill 要求归档。"""


def log(level: str, message: str):
    """写日志到文件和控制台"""
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {message}"
    print(line)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def check_single_instance():
    """检查是否已有实例在运行"""
    if PID_FILE.exists():
        try:
            with open(PID_FILE) as f:
                pid = f.read().strip()
            # 检查进程是否存在
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True, text=True
            )
            if pid in result.stdout:
                print(f"[警告] 服务已在运行 (PID: {pid})")
                print("[提示] 如需重启，请先运行 stop.bat")
                input("按回车键退出...")
                sys.exit(1)
        except:
            pass
    # 写入当前 PID
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))


def run_once():
    """执行一次分析"""
    import datetime
    start_time = time.time()
    
    log("INFO", "=" * 50)
    log("INFO", "开始执行分析任务")
    
    try:
        # 使用 kimi-cli 执行分析
        result = subprocess.run(
            [
                "kimi", "--print",
                "-p", PROMPT,
                "--work-dir", str(PROJECT_ROOT),
                "--add-dir", str(PROJECT_ROOT),
                "--output-format", "text"
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        
        # 输出结果到日志
        if result.stdout:
            for line in result.stdout.split("\n"):
                if line.strip():
                    log("INFO", f"输出: {line}")
        
        if result.stderr:
            for line in result.stderr.split("\n"):
                if line.strip():
                    log("INFO", f"信息: {line}")
        
        duration = time.time() - start_time
        log("INFO", f"任务完成，耗时 {duration:.1f} 秒，返回码: {result.returncode}")
        
        return result.returncode == 0
        
    except Exception as e:
        log("ERROR", f"执行失败: {e}")
        return False


def main():
    """主循环"""
    os.chdir(PROJECT_ROOT)
    
    print("=" * 50)
    print("财经新闻分析服务")
    print("=" * 50)
    print(f"项目目录: {PROJECT_ROOT}")
    print(f"日志文件: {LOG_FILE}")
    print(f"分析间隔: {SLEEP_SECONDS} 秒 ({SLEEP_SECONDS // 60} 分钟)")
    print("=" * 50)
    print()
    
    # 检查单实例
    check_single_instance()
    
    # 初始延迟
    if INITIAL_DELAY_SECONDS > 0:
        log("INFO", f"等待 {INITIAL_DELAY_SECONDS} 秒后首次运行...")
        time.sleep(INITIAL_DELAY_SECONDS)
    
    log("INFO", "服务启动完成，开始运行")
    
    try:
        while True:
            run_once()
            
            log("INFO", f"等待 {SLEEP_SECONDS} 秒后进行下次分析...")
            log("INFO", f"(按 Ctrl+C 停止服务)")
            print("-" * 50)
            
            time.sleep(SLEEP_SECONDS)
            
    except KeyboardInterrupt:
        log("INFO", "收到停止信号，服务退出")
    finally:
        if PID_FILE.exists():
            PID_FILE.unlink()


if __name__ == "__main__":
    main()
