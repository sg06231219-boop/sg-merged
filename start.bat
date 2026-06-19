@echo off
chcp 65001 >nul
echo ========================================
echo   自动独立站生成平台 - 启动脚本
echo ========================================
echo.

REM 查找 Python（支持多种路径）
set PYTHON_EXE=
if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    set PYTHON_EXE=%LOCALAPPDATA%\Python\bin\python.exe
) else if exist "%LOCALAPPDATA%\Programs\Python\Python3*\python.exe" (
    for /d %%i in ("%LOCALAPPDATA%\Programs\Python\Python3*") do set PYTHON_EXE=%%i\python.exe
) else (
    set PYTHON_EXE=python
)

%PYTHON_EXE% --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] 检查依赖...
%PYTHON_EXE% -m pip install -r requirements.txt -q 2>nul
if errorlevel 1 (
    echo [警告] 依赖安装失败，尝试继续...
)

echo [2/3] 启动服务...
start "" http://127.0.0.1:8866
%PYTHON_EXE% -m uvicorn apis.app:app --host 0.0.0.0 --port 8866 --reload

pause
