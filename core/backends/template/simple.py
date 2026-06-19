"""
core.backends.template.simple — 纯 Python 模板引擎（兜底）

零外部依赖，始终可用。使用内置 str.replace 进行模板渲染。
作为 Jinja2 不可用时的回退方案，类似 bcrypt 的纯 Python 实现。

相比 Jinja2，功能更简单但保证 100% 可用。
"""

from __future__ import annotations

import re
from typing import Any

from core.backends.base import TemplateBackend


class SimpleTemplateBackend(TemplateBackend):
    """
    纯 Python 模板引擎。

    优先级 999（始终兜底）。零依赖，永远可用。
    使用简单的变量替换和 for 循环语法渲染模板。
    """

    name = "simple"
    priority = 999

    # 模板语法：
    #   {{ var }}       → 变量替换（自动 HTML 转义）
    #   {{ var | safe }} → 不转义
    #   {% for item in list %}...{% endfor %} → 循环

    _VAR_RE = re.compile(r"\{\{\s*(\w+)\s*(?:\|\s*safe\s*)?\s*\}\}")
    _FOR_RE = re.compile(r"\{\%\s*for\s+(\w+)\s+in\s+(\w+)\s*\%\}(.*?)\{\%\s*endfor\s*\%\}", re.DOTALL)
    _IF_RE = re.compile(r"\{\%\s*if\s+(\w+)\s*\%\}(.*?)\{\%\s*endif\s*\%\}", re.DOTALL)

    def __init__(self):
        pass

    @classmethod
    def _check_dependencies(cls) -> None:
        """始终可用，无需检查"""
        pass

    def render(self, template: str, context: dict[str, Any]) -> str:
        """渲染模板字符串"""
        if isinstance(template, str) and template in self._BUILTIN:
            template = self._BUILTIN[template]
        return self._render_str(template, context)

    def render_site(self, pages: dict[str, str], context: dict[str, Any]) -> dict[str, str]:
        """渲染多页"""
        return {name: self._render_str(tmpl, context) for name, tmpl in pages.items()}

    def _render_str(self, template: str, context: dict) -> str:
        """核心渲染逻辑"""
        result = template

        # 1. 处理 for 循环
        def _replace_for(m):
            var_name = m.group(1)
            list_name = m.group(2)
            inner = m.group(3)
            items = context.get(list_name, [])
            if not items:
                return ""
            parts = []
            for item in items:
                if isinstance(item, dict):
                    part = inner
                    for ik, iv in item.items():
                        part = part.replace("{{ " + ik + " }}", self._escape(str(iv)))
                        part = part.replace("{{ " + ik + " | safe }}", str(iv))
                    parts.append(part)
                else:
                    parts.append(inner.replace("{{ " + var_name + " }}", self._escape(str(item))))
            return "".join(parts)

        # 多次替换处理嵌套循环（简单场景足够）
        for _ in range(5):
            new_result = self._FOR_RE.sub(_replace_for, result)
            if new_result == result:
                break
            result = new_result

        # 2. 处理 if 条件
        def _replace_if(m):
            cond = m.group(1)
            inner = m.group(2)
            return inner if context.get(cond) else ""

        result = self._IF_RE.sub(_replace_if, result)

        # 3. 处理 {{ var | safe }}
        safe_re = re.compile(r"\{\{\s*(\w+)\s*\|\s*safe\s*\}\}")
        result = safe_re.sub(lambda m: str(context.get(m.group(1), "")), result)

        # 4. 处理 {{ var }}
        var_re = re.compile(r"\{\{\s*(\w+)\s*\}\}")
        result = var_re.sub(lambda m: self._escape(str(context.get(m.group(1), ""))), result)

        return result

    @staticmethod
    def _escape(s: str) -> str:
        """HTML 转义（类似 Jinja2 的 autoescape）"""
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")

    # ── 内置模板（与 Jinja2 后端保持一致）──
    _BUILTIN = {
        "landing": """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ meta_title }}</title>
<meta name="description" content="{{ meta_description }}">
<meta name="keywords" content="{{ meta_keywords }}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{{ canonical_url }}">
<meta property="og:title" content="{{ meta_title }}">
<meta property="og:description" content="{{ meta_description }}">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:#333;line-height:1.6;background:#f5f7fa}
.container{max-width:1200px;margin:0 auto;padding:0 24px}
nav{background:#fff;box-shadow:0 2px 8px rgba(0,0,0,.06);position:sticky;top:0;z-index:100}
nav .container{display:flex;align-items:center;justify-content:space-between;height:64px}
nav .logo{font-size:22px;font-weight:700;color:{{ primary_color }}}
nav .links{display:flex;gap:28px}
nav .links a{text-decoration:none;color:#555;font-size:14px}
nav .links a:hover{color:{{ primary_color }}}
.hero{background:linear-gradient(135deg,{{ primary_color }},{{ primary_dark }});color:#fff;padding:80px 0;text-align:center}
.hero h1{font-size:42px;margin-bottom:16px}
.hero p{font-size:18px;opacity:.9;margin-bottom:32px;max-width:600px;margin:0 auto 32px}
.hero .btn{display:inline-block;background:#fff;color:{{ primary_color }};padding:14px 40px;border-radius:8px;font-weight:700;text-decoration:none;font-size:16px;transition:transform .2s}
.hero .btn:hover{transform:scale(1.05)}
.features{padding:80px 0}
.features h2{text-align:center;font-size:32px;margin-bottom:48px}
.fgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:32px}
.fcard{background:#fff;padding:32px;border-radius:12px;box-shadow:0 2px 16px rgba(0,0,0,.04);transition:transform .2s}
.fcard:hover{transform:translateY(-4px)}
.fcard h3{font-size:20px;color:{{ primary_color }};margin-bottom:12px}
.about{background:#fff;padding:80px 0}
.about h2{text-align:center;font-size:32px;margin-bottom:32px}
.about-inner{max-width:800px;margin:0 auto;line-height:2;color:#555}
.testimonials{padding:80px 0;background:{{ primary_light }}}
.testimonials h2{text-align:center;font-size:32px;margin-bottom:48px}
.tgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:24px}
.tcard{background:#fff;padding:28px;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,.04)}
.tcard blockquote{font-size:16px;color:#555;line-height:1.8;margin-bottom:16px;font-style:italic}
.tcard .author{font-weight:600;color:{{ primary_color }}}
.faq{padding:80px 0}
.faq h2{text-align:center;font-size:32px;margin-bottom:48px}
.faq-list{max-width:800px;margin:0 auto}
.faq-item{background:#fff;padding:24px 28px;margin-bottom:12px;border-radius:8px;box-shadow:0 1px 6px rgba(0,0,0,.03)}
.faq-item h4{font-size:17px;color:{{ primary_color }};margin-bottom:8px}
.cta{background:linear-gradient(135deg,{{ primary_color }},{{ primary_dark }});color:#fff;padding:80px 0;text-align:center}
.cta h2{font-size:36px;margin-bottom:16px}
.cta p{font-size:18px;margin-bottom:32px;opacity:.9}
.cta .btn{display:inline-block;background:#fff;color:{{ primary_color }};padding:14px 40px;border-radius:8px;font-weight:700;text-decoration:none;font-size:16px}
footer{background:{{ footer_bg }};color:{{ footer_text }};text-align:center;padding:32px 0;font-size:14px}
</style>
</head>
<body>
<nav><div class="container"><div class="logo">{{ hero_headline }}</div><div class="links"><a href="#features">特色</a><a href="#about">关于</a><a href="#faq">FAQ</a><a href="#cta">联系</a></div></div></nav>
<section class="hero"><div class="container"><h1>{{ hero_headline }}</h1><p>{{ hero_subheadline }}</p><a href="#cta" class="btn">{{ hero_cta }}</a></div></section>
<section class="features" id="features"><div class="container"><h2>{{ features_title }}</h2><div class="fgrid">
{% for f in features %}<div class="fcard"><h3>{{ f.title }}</h3><p>{{ f.description }}</p></div>{% endfor %}
</div></div></section>
<section class="about" id="about"><div class="container"><h2>{{ about_title }}</h2><div class="about-inner">{{ about_content | safe }}</div></div></section>
{% if testimonials %}<section class="testimonials"><div class="container"><h2>{{ testimonials_title }}</h2><div class="tgrid">
{% for t in testimonials %}<div class="tcard"><blockquote>"{{ t.text }}"</blockquote><div class="author">— {{ t.name }}</div></div>{% endfor %}
</div></div></section>{% endif %}
{% if faq %}<section class="faq" id="faq"><div class="container"><h2>{{ faq_title }}</h2><div class="faq-list">
{% for item in faq %}<div class="faq-item"><h4>❓ {{ item.q }}</h4><p>{{ item.a }}</p></div>{% endfor %}
</div></div></section>{% endif %}
<section class="cta" id="cta"><div class="container"><h2>{{ cta_headline }}</h2><p>{{ cta_subheadline }}</p><a href="#" class="btn">{{ cta_button }}</a></div></section>
<footer><p>{{ footer_text }}</p></footer>
</body>
</html>""",
    }