"""
core.config — 企业级配置管理

特性：
- 环境隔离（dev/staging/production）
- 类型安全的配置验证（Pydantic）
- 敏感信息环境变量注入
- 默认值合理，零配置可启动
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class DatabaseConfig(BaseSettings):
    """数据库配置"""
    url: str = Field(default="", description="数据库URL，留空自动使用SQLite")
    pool_size: int = Field(default=5, ge=1, le=50, description="连接池大小")
    max_overflow: int = Field(default=10, ge=0, le=50, description="连接池最大溢出")
    pool_pre_ping: bool = Field(default=True, description="连接健康检查")

    model_config = {"env_prefix": "DB_"}


class RedisConfig(BaseSettings):
    """Redis配置"""
    url: str = Field(default="redis://localhost:6379/0", description="Redis连接URL")
    enabled: bool = Field(default=False, description="是否启用Redis（False时降级到内存）")
    password: Optional[str] = Field(default=None, description="Redis密码")
    max_connections: int = Field(default=20, ge=1, le=100, description="最大连接数")
    socket_timeout: float = Field(default=5.0, ge=1.0, le=30.0, description="连接超时(秒)")

    model_config = {"env_prefix": "REDIS_"}


class RateLimitConfig(BaseSettings):
    """限流配置"""
    enabled: bool = Field(default=True, description="是否启用限流")
    backend: str = Field(default="memory", description="限流后端: memory | redis")
    generate_per_minute: int = Field(default=10, ge=1, le=1000, description="生成接口每分钟限制")
    preview_per_minute: int = Field(default=60, ge=1, le=1000, description="预览接口每分钟限制")
    download_per_minute: int = Field(default=30, ge=1, le=1000, description="下载接口每分钟限制")
    default_per_minute: int = Field(default=100, ge=1, le=10000, description="默认每分钟限制")
    auth_per_minute: int = Field(default=10, ge=1, le=100, description="认证接口每分钟限制")
    anon_daily_limit: int = Field(default=3, ge=1, le=100, description="未登录用户每日限制")

    model_config = {"env_prefix": "RATELIMIT_"}


class CacheConfig(BaseSettings):
    """缓存配置"""
    enabled: bool = Field(default=True, description="是否启用语义缓存")
    backend: str = Field(default="memory", description="缓存后端: memory | redis")
    max_entries: int = Field(default=200, ge=10, le=10000, description="内存缓存最大条目")
    ttl_seconds: int = Field(default=3600, ge=60, le=86400, description="缓存TTL(秒)")
    redis_ttl_seconds: int = Field(default=7200, ge=60, le=86400, description="Redis缓存TTL(秒)")

    model_config = {"env_prefix": "CACHE_"}


class SecurityConfig(BaseSettings):
    """安全配置"""
    jwt_secret: str = Field(default="", description="JWT签名密钥，留空自动生成")
    jwt_expire_hours: int = Field(default=72, ge=1, le=720, description="JWT过期时间(小时)")
    admin_password: str = Field(default="", description="管理员密码")
    cors_origins: str = Field(
        default="http://localhost:8000,http://localhost:3000",
        description="CORS白名单(逗号分隔)"
    )
    hsts_max_age: int = Field(default=31536000, description="HSTS max-age(秒)")
    csp_report_only: bool = Field(default=False, description="CSP是否仅报告模式")

    model_config = {"env_prefix": "SECURITY_"}


class ObservabilityConfig(BaseSettings):
    """可观测性配置"""
    log_level: str = Field(default="INFO", description="日志级别")
    log_format: str = Field(default="json", description="日志格式: json | text")
    log_file: Optional[str] = Field(default=None, description="日志文件路径，None则仅控制台")
    log_max_bytes: int = Field(default=10_485_760, description="日志文件最大字节数(默认10MB)")
    log_backup_count: int = Field(default=5, description="日志文件备份数量")
    metrics_enabled: bool = Field(default=True, description="是否启用Prometheus指标")
    metrics_path: str = Field(default="/metrics", description="指标端点路径")
    request_id_header: str = Field(default="X-Request-ID", description="请求追踪ID头")

    model_config = {"env_prefix": "OBS_"}

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"log_level must be one of {valid}")
        return upper

    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        valid = {"json", "text"}
        if v not in valid:
            raise ValueError(f"log_format must be one of {valid}")
        return v


class AIConfig(BaseSettings):
    """AI后端配置"""
    default_backend: str = Field(default="auto", description="默认AI后端: auto | deepseek | glm | mock")
    deepseek_api_key: str = Field(default="", description="DeepSeek API Key")
    deepseek_base_url: str = Field(default="https://api.deepseek.com/v1", description="DeepSeek API Base URL")
    glm_api_key: str = Field(default="", description="智谱GLM API Key")
    glm_base_url: str = Field(default="https://open.bigmodel.cn/api/paas/v4", description="GLM API Base URL")
    timeout_seconds: float = Field(default=30.0, ge=5.0, le=120.0, description="AI请求超时(秒)")
    max_retries: int = Field(default=2, ge=0, le=5, description="AI请求最大重试次数")

    model_config = {"env_prefix": "AI_"}


class AppConfig(BaseSettings):
    """应用全局配置"""
    app_name: str = Field(default="SG智能建站", description="应用名称")
    environment: Environment = Field(default=Environment.DEVELOPMENT, description="运行环境")
    version: str = Field(default="9.0.0", description="应用版本")
    port: int = Field(default=10000, ge=1, le=65535, description="服务端口")
    debug: bool = Field(default=False, description="调试模式")
    site_domain: str = Field(default="localhost:8000", description="站点域名")

    # 子配置
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    ai: AIConfig = Field(default_factory=AIConfig)

    model_config = {"env_prefix": "APP_"}

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        return self.environment == Environment.DEVELOPMENT

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip() for o in self.security.cors_origins.split(",") if o.strip()]
        if self.is_development:
            origins.extend(["http://127.0.0.1:8000", "http://127.0.0.1:3000"])
        return list(set(origins))


# ── 全局配置单例 ──────────────────────────────────────
_config: AppConfig | None = None


def get_config() -> AppConfig:
    """获取全局配置单例"""
    global _config
    if _config is None:
        _config = AppConfig()
    return _config


def reload_config() -> AppConfig:
    """强制重新加载配置"""
    global _config
    _config = AppConfig()
    return _config
