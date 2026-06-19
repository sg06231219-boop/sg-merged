"""
core.loaders — 动态后端加载器

仿 passlib 的 bcrypt 后端加载机制：
- 按优先级依次尝试加载每个后端
- 加载成功则注册，失败则跳过
- 自动选择最优可用后端
- 支持手动切换和热重载

类比关系:
  passlib.bcrypt._load_backend_mixin(name, dryrun)
    → loaders._load_ai_backend(name, dryrun)

  json 模块: c_scanstring or py_scanstring
    → deepseek or glm or mock
"""

from __future__ import annotations

import logging
from typing import Any

from core.backends.base import SubclassBackendMixin

logger = logging.getLogger("site-builder.loaders")


# ═══════════════════════════════════════════════════════════
#  AI 后端加载器
# ═══════════════════════════════════════════════════════════

class AIBackendLoader(SubclassBackendMixin):
    """
    AI 后端的动态加载器。

    Engine 通过此类加载 AI 后端，无需关心具体实现。
    类似 bcrypt 通过 SubclassBackendMixin 加载 C 或 Python 实现。
    """

    _backend_type = "ai"
    _backend_registry: dict = {}
    _active_backend = None
    _active_backend_name: str = ""
    _backend_priority_order: list = []

    @classmethod
    def load_default(cls, config: dict | None = None) -> str:
        """
        按优先级加载 AI 后端（类似 bcrypt.set_backend("any")）。

        Args:
            config: 可选配置，可覆盖后端优先级
        Returns:
            加载成功的后端名称
        """
        cls._register_all()
        init_kwargs = {}

        if config:
            for key in ("api_key", "model", "base_url"):
                if key in config:
                    init_kwargs[key] = config[key]

        return cls.set_backend("any", **init_kwargs)

    @classmethod
    def _register_all(cls) -> None:
        """导入并注册所有 AI 后端（类似 bcrypt 发现子类）"""
        from core.backends.ai.mock import MockAIBackend
        cls.register_backend(MockAIBackend)

        # DeepSeek — 优先使用（类似 bcrypt 的 C 扩展）
        try:
            from core.backends.ai.deepseek import DeepSeekBackend
            cls.register_backend(DeepSeekBackend)
        except ImportError:
            logger.debug("DeepSeek 后端不可用")

        # GLM — 次选
        try:
            from core.backends.ai.glm import GLMBackend
            cls.register_backend(GLMBackend)
        except ImportError:
            logger.debug("GLM 后端不可用")


# ═══════════════════════════════════════════════════════════
#  模板后端加载器
# ═══════════════════════════════════════════════════════════

class TemplateBackendLoader(SubclassBackendMixin):
    """
    模板后端加载器。

    Jinja2 优先（功能完整），Simple 兜底（零依赖）。
    """

    _backend_type = "template"
    _backend_registry: dict = {}
    _active_backend = None
    _active_backend_name: str = ""
    _backend_priority_order: list = []

    @classmethod
    def load_default(cls) -> str:
        cls._register_all()
        return cls.set_backend("any")

    @classmethod
    def _register_all(cls) -> None:
        try:
            from core.backends.template.simple import SimpleTemplateBackend
            cls.register_backend(SimpleTemplateBackend)
        except ImportError:
            logger.debug("Simple 后端不可用")

        try:
            from core.backends.template.jinja2 import Jinja2TemplateBackend
            cls.register_backend(Jinja2TemplateBackend)
        except ImportError:
            logger.debug("Jinja2 后端不可用")