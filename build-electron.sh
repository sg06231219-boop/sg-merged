#!/bin/bash
export ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/
echo "==================================="
echo " 构建 Electron 桌面应用"
echo "==================================="
npm install --save-dev electron electron-builder
npx electron-builder --win portable
echo "✅ 完成！查看 dist-electron/ 目录"