# SG智能建站 — 变更日志

所有重要变更记录于此。格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/)。

## [8.0.0] - 2026-05-26

### 新增 — 企业级基础架构
- **SQLAlchemy ORM + Alembic 迁移**：10张数据表（Tenant/User/Site/Product/Order/Inquiry/ActivationCode/AIUsage/Subscription/Cart）
- **多租户架构**：租户隔离，支持 free/pro/enterprise 三档
- **RBAC 权限**：super_admin/admin/member/viewer 四级角色
- **Docker Compose**：PostgreSQL + Redis + App 一键部署
- **测试框架**：pytest + 10个模型单元测试全部通过
- **Alembic 数据库迁移**：版本化 schema 管理
- **.env.example**：环境变量模板
- **LICENSE**：MIT 开源协议
- **Makefile**：开发/测试/部署命令入口
- **.dockerignore**：Docker 构建优化

### 技术栈
- Python 3.12+ / FastAPI / SQLAlchemy 2.0 / Alembic
- PostgreSQL（生产）/ SQLite（开发）
- Docker / Docker Compose
- pytest

## [7.13.0] - 2026-05-25

### 已有功能
- AI建站引擎（Landing/Pricing/Site/Shop 四模式）
- 7个AI工具（SEO/文案/竞品/命名/短剧/UniPulse/去水印）
- 虎皮椒支付集成
- 询盘系统
- 安全审计33项修复
