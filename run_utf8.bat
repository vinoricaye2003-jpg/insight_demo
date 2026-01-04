@echo off
chcp 65001 > nul
echo ================================================================================
echo XHS-MarketAI System - 启动中...
echo ================================================================================
echo.

.venv\Scripts\python.exe market_insight_system.py

pause
