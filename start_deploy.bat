@echo off
chcp 65001 >nul
title Auto Site Builder - Deploy

echo ============================================================
echo  自动独立站生成平台 - 一键部署公网
echo ============================================================
echo.

REM === 检测端口是否被占用 ===
netstat -ano | findstr ":8880" >nul
if %ERRORLEVEL% EQU 0 (
    echo [!] 端口 8880 已被占用，正在使用，尝试关闭旧进程...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8880" ^| findstr "LISTENING"') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    timeout /t 2 /nobreak >nul
)

REM === 启动服务器 ===
echo [1] 启动服务器 (localhost:8880)...
start /b cmd /k "cd /d "%~dp0" && python -m uvicorn apis.app:app --host 0.0.0.0 --port 8880"
timeout /t 5 /nobreak >nul

REM === 检查服务器是否启动成功 ===
python -c "import requests; r=requests.get('http://127.0.0.1:8880/api/v1/health',timeout=5); print('OK' if r.status_code==200 else 'FAIL')" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [X] 服务器启动失败! 请检查 Python 环境
    pause
    exit /b 1
)
echo [OK] 服务器已启动

REM === 启动 Cloudflare Tunnel ===
echo [2] 创建公网隧道...
echo     (按 Ctrl+C 停止隧道)
echo.
echo ============================================================
echo.

REM === 启动 cloudflared 并输出 URL ===
tools\cloudflared.exe tunnel --url http://localhost:8880 --no-autoupdate

REM 按任意键退出（如果用户手动停止隧道）
pause >nul