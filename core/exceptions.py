"""
core.exceptions — 项目自定义异常

用于清晰区分不同层级的错误，便于上层统一捕获和处理。
"""


class SiteBuilderError(Exception):
    """站点构建器的基类异常"""
    pass


class BackendNotFoundError(SiteBuilderError):
    """所有候选后端均不可用时抛出"""
    def __init__(self, category: str, tried: list[str] | None = None):
        self.category = category
        self.tried = tried or []
        tried_str = ", ".join(self.tried) if self.tried else "无"
        super().__init__(f"未找到可用的 {category} 后端。尝试过: {tried_str}")


class BackendInitError(SiteBuilderError):
    """后端初始化失败时抛出"""
    def __init__(self, backend_name: str, reason: str):
        self.backend_name = backend_name
        self.reason = reason
        super().__init__(f"后端 {backend_name} 初始化失败: {reason}")


class AIGenerationError(SiteBuilderError):
    """AI 内容生成失败"""
    def __init__(self, provider: str, detail: str):
        self.provider = provider
        self.detail = detail
        super().__init__(f"[{provider}] AI 生成失败: {detail}")


class TemplateRenderError(SiteBuilderError):
    """模板渲染失败"""
    def __init__(self, engine: str, detail: str):
        self.engine = engine
        self.detail = detail
        super().__init__(f"[{engine}] 模板渲染失败: {detail}")


class ConfigurationError(SiteBuilderError):
    """配置文件错误"""
    pass
