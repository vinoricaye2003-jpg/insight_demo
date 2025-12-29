@echo off
echo ========================================
echo XHS-MarketAI System - Quick Setup
echo ========================================
echo.

echo [1/4] Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo Error: Failed to create virtual environment
    pause
    exit /b 1
)

echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat

echo [3/4] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install dependencies
    pause
    exit /b 1
)

echo [4/4] Setup complete!
echo.
echo ========================================
echo Next Steps:
echo ========================================
echo 1. Set your DeepSeek API key:
echo    $env:DEEPSEEK_API_KEY="your_key_here"
echo.
echo 2. Run the system:
echo    python market_insight_system.py
echo.
echo ========================================
pause
