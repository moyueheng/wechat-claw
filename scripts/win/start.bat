@echo off
chcp 65001 >nul
title 财经新闻分析系统 - 启动中

cd /d "%~dp0\..\.."

echo ========================================
echo   财经新闻分析系统
echo ========================================
echo.

:: 检查 .env
echo [检查] 检查配置...
if not exist ".env" (
    echo [错误] 未找到 .env 文件，请先配置飞书信息
    pause
    exit /b 1
)

:: 安装依赖
echo [安装] 检查依赖...
uv sync >nul 2>&1

:: 启动新闻采集（后台窗口）
echo [启动] 启动新闻采集服务...
start "新闻采集" uv run python -m eastmoney_kuaixun.daemon --daemon

:: 启动新闻分析（后台窗口）  
echo [启动] 启动新闻分析服务...
start "新闻分析" uv run python scripts/win/run_analysis.py

echo.
echo ========================================
echo [完成] 系统已启动！
echo.
echo 两个黑色窗口会保持运行：
echo   - 新闻采集：获取东方财富新闻
echo   - 新闻分析：分析新闻并发送到飞书
echo.
echo 关闭本窗口不会影响服务运行
echo 如需停止，请双击 stop.bat
echo ========================================
pause
