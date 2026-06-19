"""core — 自动独立站生成平台核心模块

包含 SiteBuilderEngine、动态后端加载器、AI/模板后端等核心组件。

架构模式参考:
  passlib.bcrypt → SubclassBackendMixin + 自动后端选择
  json 模块 → c_scanstring or py_scanstring 快速通道
  asyncio → BaseEventLoop 统一接口，子类实现具体事件循环
"""