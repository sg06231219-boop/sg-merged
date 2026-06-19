@echo off
chcp 65001 >nul
set ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/
echo ============================================
echo  自动独立站生成平台 — Electron 桌面版打包
echo ============================================
echo.
echo [1/3] 检查依赖...
if not exist "node_modules" (
    echo [安装] npm install...
    call npm install --save-dev electron electron-builder
)
echo [2/3] 开始打包桌面应用...
call npx electron-builder --win portable
echo.
if exist "dist-electron\AutoSiteBuilder-*-portable.exe" (
    echo [3/3] ✅ 打包完成！
    dir /b dist-electron\AutoSiteBuilder-*-portable.exe
) else (
    echo [3/3] 打包文件请查看 dist-electron\ 目录
    dir /b dist-electron\*.exe 2>nul
)
echo.
echo 双击 .exe 文件即可运行桌面应用 🚀
pause