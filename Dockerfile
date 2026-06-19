FROM python:3.12-slim

LABEL maintainer="SG Builder"
LABEL description="SG智能建站 — AI驱动的程序化SEO建站引擎"

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 项目代码
COPY . .

# 创建数据目录
RUN mkdir -p /app/data /app/outputs

# 非root用户运行
RUN useradd -m -d /app appuser && chown -R appuser:appuser /app
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:10000/api/v1/health')" || exit 1

EXPOSE 10000

# 启动命令
CMD ["uvicorn", "apis.app:app", "--host", "0.0.0.0", "--port", "10000"]
