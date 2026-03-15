@echo off
chcp 65001 >nul
title 财经新闻分析系统 - 停止

echo ========================================
echo   正在停止服务...
echo ========================================
echo.

taskkill /FI "WINDOWTITLE eq 新闻采集*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq 新闻分析*" /F >nul 2>&1
taskkill /IM python.exe /F >nul 2>&1

echo [完成] 服务已停止
echo ========================================
pause
