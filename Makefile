# SG智能建站 Makefile
# 通用命令入口

.PHONY: help dev test db-migrate db-upgrade lint clean docker-up docker-down

help: ## 显示帮助
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: ## 本地开发启动
	uvicorn apis.app:app --host 0.0.0.0 --port 10000 --reload

test: ## 运行测试
	pytest tests/ -v --tb=short

test-cov: ## 运行测试+覆盖率
	pytest tests/ -v --cov=core --cov=apis --cov-report=term-missing

db-migrate: ## 创建数据库迁移
	alembic revision --autogenerate -m "$(msg)"

db-upgrade: ## 执行数据库迁移
	alembic upgrade head

db-downgrade: ## 回滚数据库迁移
	alembic downgrade -1

lint: ## 代码检查
	python -m py_compile apis/app.py
	python -m py_compile core/engine.py
	python -m py_compile core/models.py
	@echo "✅ Syntax check passed"

clean: ## 清理临时文件
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache
	@echo "✅ Cleaned"

docker-up: ## Docker Compose 启动
	docker compose up -d

docker-down: ## Docker Compose 停止
	docker compose down

docker-logs: ## Docker 查看日志
	docker compose logs -f app

docker-build: ## Docker 重新构建
	docker compose build --no-cache
