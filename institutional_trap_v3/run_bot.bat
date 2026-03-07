@echo off
title Institutional Trap v3.0 - Deriv MT5 Auto-Trading Bot
color 0A

echo ============================================
echo   Institutional Trap v3.0
echo   Deriv Volatility 25 Auto-Trading Bot
echo ============================================
echo.
echo Starting bot...
echo.

cd /d %~dp0

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python 3.10+
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist .env (
    echo WARNING: .env file not found!
    echo Creating from .env.example...
    copy .env.example .env
    echo.
    echo IMPORTANT: Edit .env file with your Telegram credentials before running!
    echo Press any key to open .env file in Notepad...
    pause >nul
    notepad .env
    echo.
    echo After saving .env, run the bot again
    pause
    exit /b 1
)

REM Check if requirements are installed
python -c "import MetaTrader5" >nul 2>&1
if errorlevel 1 (
    echo Installing required packages...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies!
        pause
        exit /b 1
    )
)

echo.
echo ============================================
echo Bot is starting...
echo Press Ctrl+C to stop the bot
echo ============================================
echo.

REM Run the bot
python main.py

if errorlevel 1 (
    echo.
    echo ============================================
    echo Bot stopped with an error
    echo Check the logs for details
    echo ============================================
    pause
)
