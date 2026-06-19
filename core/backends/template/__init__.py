"""
core.backends.template — 模板渲染后端包
"""

from core.backends.template.jinja2 import Jinja2TemplateBackend
from core.backends.template.simple import SimpleTemplateBackend

__all__ = ["Jinja2TemplateBackend", "SimpleTemplateBackend"]