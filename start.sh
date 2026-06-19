#!/bin/bash
# ========================================
#   自动独立站生成平台 - 启动脚本
# ========================================

echo "========================================"
echo "  自动独立站生成平台 - 启动脚本"
echo "========================================"
echo ""

# 查找 Python
PYTHON_EXE=""
if command -v python3 &>/dev/null; then
    PYTHON_EXE=python3
elif command -v python &>/dev/null; then
    PYTHON_EXE=python
else
    echo "[错误] 未找到 Python，请先安装 Python 3.10+"
    echo "下载地址: https://www.python.org/downloads/"
    exit 1
fi

echo "[1/3] 检查依赖..."
$PYTHON_EXE -m pip install -r requirements.txt -q 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[警告] 依赖安装失败，尝试继续..."
fi

echo "[2/3] 启动服务..."
echo ""
echo "  🌐 前端页面: http://127.0.0.1:8866"
echo "  📖 API文档:  http://127.0.0.1:8866/docs"
echo ""

# 尝试打开浏览器
if command -v open &>/dev/null; then
    open http://127.0.0.1:8866 2>/dev/null &
elif command -v xdg-open &>/dev/null; then
    xdg-open http://127.0.0.1:8866 2>/dev/null &
fi

$PYTHON_EXE -m uvicorn apis.app:app --host 0.0.0.0 --port 8866 --reload