"""
core.backends.base — 后端抽象 + SubclassBackendMixin 动态混入机制

设计灵感来自 passlib.hash.bcrypt 的 SubclassBackendMixin 模式：
- 定义抽象后端接口，不绑定具体实现
- 运行时动态检测可用后端，按优先级自动选择
- 支持手动切换后端（前端选择模型）
- 后端失败时自动回退到下一优先级

核心类：
  AIBackend         — AI 生成后端抽象（→ DeepSeek / GLM / Mock）
  TemplateBackend   — 模板渲染后端抽象（→ Jinja2 / SimplePython）
  SubclassBackendMixin — 混入到 BuilderEngine，提供动态加载能力
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any

from core.exceptions import BackendNotFoundError, BackendInitError

logger = logging.getLogger("site-builder.backends")


# ═══════════════════════════════════════════════════════════
#  后端抽象接口
# ═══════════════════════════════════════════════════════════

class AIBackend(ABC):
    """
    AI 内容生成后端的抽象接口。

    每个具体实现（DeepSeek、GLM、Mock）继承此类并实现 generate 方法。
    子类需定义类属性: name / priority / display_name
    """

    name: str = "__abstract__"
    priority: int = 100  # 越小越优先，类似 passlib 的优先级机制
    display_name: str = "抽象后端"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r} pri={self.priority}>"

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> dict[str, Any]:
        """调用 AI 生成结构化 JSON 内容。返回一个字典。"""
        ...

    async def health_check(self) -> bool:
        """检测后端是否可用（连接性 / API Key 检查）。默认返回 True。"""
        return True


class TemplateBackend(ABC):
    """
    模板渲染后端的抽象接口。

    每个具体实现（Jinja2、Simple）继承此类并实现 render 方法。
    """

    name: str = "__abstract__"
    priority: int = 100

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r} pri={self.priority}>"

    @abstractmethod
    def render(self, template: str, context: dict[str, Any]) -> str:
        """渲染模板字符串，返回完整的 HTML。"""
        ...

    @abstractmethod
    def render_site(self, pages: dict[str, str], context: dict[str, Any]) -> dict[str, str]:
        """
        渲染多页站点（如首页 / 关于 / 产品 / 博客 / 联系）。
        pages: {page_name: template_content}，返回 {page_name: rendered_html}
        """
        ...


# ═══════════════════════════════════════════════════════════
#  SubclassBackendMixin — 仿 passlib 的动态后端混入
# ═══════════════════════════════════════════════════════════

class SubclassBackendMixin:
    """
    动态后端混入机制。

    仿照 passlib 的 SubclassBackendMixin（见 bcrypt.py）：
    1. 子类通过 __init_subclass__ 自动注册为"后端候选"
    2. set_backend(name) 运行时切换后端
    3. 切换失败时自动回退到下一优先级
    4. 支持 "any" 模式自动检测最优后端

    用法:
        class SiteBuilderEngine(SubclassBackendMixin):
            _backend_type = "ai"  # 标记这个类管理的是哪种后端

        class DeepSeekBackend(AIBackend, SiteBuilderEngine):
            name = "deepseek"
            priority = 1
            ...

        # 自动选择: engine.set_backend("any")
        # 手动选择: engine.set_backend("deepseek")

    类似于 asyncio 的 BaseEventLoop 定义统一接口后，
    由 SelectorEventLoop / ProactorEventLoop 实现具体多路复用；
    类似于 json 中 c_scanstring or py_scanstring 的快速通道回退。
    """

    # --- 类级别状态 ---
    _backend_registry: dict[str, type] = {}   # {name: backend_cls}
    _active_backend = None                     # 当前激活的后端实例
    _active_backend_name: str = ""             # 当前后端名称
    _backend_type: str = ""                    # 后端类别标识（ai / template）
    _backend_priority_order: list[str] = []    # 按优先级排序的后端名称列表

    @classmethod
    def _discover_backends(cls) -> None:
        """发现所有注册到当前类的后端子类（由 __init_subclass__ 钩子自动维护）"""
        pass  # 子类通过 register_backend 手动注册

    @classmethod
    def register_backend(cls, backend_cls: type) -> None:
        """
        注册一个后端类。
        在 backends/ai/__init__.py 或 loaders 中导入后端时调用。
        """
        if not hasattr(backend_cls, "name") or not backend_cls.name:
            raise BackendInitError(
                backend_cls.__name__, "后端必须定义 name 类属性"
            )
        name = backend_cls.name
        cls._backend_registry[name] = backend_cls
        logger.debug(f"[{cls._backend_type}] 注册后端: {name} (pri={getattr(backend_cls, 'priority', '?')})")

    @classmethod
    def get_available_backends(cls) -> list[str]:
        """返回当前可用的后端名称列表（按优先级排序）"""
        available = []
        for name, be_cls in cls._backend_registry.items():
            try:
                # 检查依赖是否可用（类似 bcrypt 的 _load_backend 检测）
                be_cls._check_dependencies()
                available.append((getattr(be_cls, "priority", 100), name))
            except Exception:
                logger.debug(f"[{cls._backend_type}] 后端 {name} 环境不满足，跳过")
        available.sort()
        return [name for _, name in available]

    @classmethod
    def set_backend(cls, name: str = "any", **init_kwargs) -> str:
        """
        切换当前激活的后端。

        流程仿 bcrypt._set_backend：
        1. 传入后端名称或 "any"
        2. 如果是 "any"：按优先级依次尝试，取第一个可用的
        3. 如果是具体名称：尝试加载，失败则抛异常
        4. 调用 _finalize_backend_mixin 完成混入

        返回实际激活的后端名称。
        """
        if name == "any":
            available = cls.get_available_backends()
            if not available:
                raise BackendNotFoundError(
                    cls._backend_type or "unknown",
                    list(cls._backend_registry.keys()),
                )
            # 取优先级最高的
            name = available[0]
            logger.info(f"[{cls._backend_type}] auto 选择后端: {name} (available: {available})")

        if name not in cls._backend_registry:
            raise BackendNotFoundError(
                cls._backend_type or "unknown",
                [name],
            )

        backend_cls = cls._backend_registry[name]
        try:
            backend_cls._check_dependencies()
        except Exception as e:
            raise BackendInitError(name, str(e))

        # 将选中的后端混入当前类（仿 passlib 的 _finalize_backend_mixin）
        cls._finalize_backend_mixin(name, backend_cls, **init_kwargs)
        cls._active_backend_name = name
        logger.info(f"[{cls._backend_type}] 后端已激活: {name}")
        return name

    @classmethod
    def _finalize_backend_mixin(cls, name: str, backend_cls: type, **init_kwargs) -> None:
        """
        将选中的后端混入当前类。

        仿 passlib 的 _finalize_backend_mixin，它会在运行时将
        后端子类的所有方法复制到父类上，修改继承链。

        这里采用更可控的"委托"方式：激活的后端实例存为类变量，
        引擎方法调用时转发到该实例。
        """
        try:
            instance = backend_cls(**init_kwargs)
        except Exception as e:
            raise BackendInitError(name, f"实例化失败: {e}")
        cls._active_backend = instance

    @classmethod
    def get_backend(cls) -> str:
        """返回当前激活的后端名称"""
        return cls._active_backend_name

    @classmethod
    def get_backend_instance(cls):
        """返回当前激活的后端实例"""
        return cls._active_backend


# ═══════════════════════════════════════════════════════════
#  后端注册辅助：用 __init_subclass__ 自动注册
# ═══════════════════════════════════════════════════════════

class AutoRegisterBackendMeta(type):
    """
    元类：任何继承自使用此元类的类的子类自动注册。

    类似于 passlib 中 bcrypt 后端的 __init_subclass__ 钩子，
    但通过元类实现更干净的跨类别注册。
    """

    _registry_target = None  # 子类需指定注册到哪个 Mixin

    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)
        if mcs._registry_target is not None and hasattr(cls, "name") and cls.name not in ("__abstract__", ""):
            mcs._registry_target.register_backend(cls)
        return cls
