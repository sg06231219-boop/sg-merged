"""
core.backends.template.jinja2 - Jinja2 模板引擎后端(SG v4.0 营收引擎版)

交互增强版:所有生成页面包含完整JS交互 + 转化漏斗组件
- 平滑滚动导航
- 移动端汉堡菜单
- FAQ手风琴折叠
- CTA表单提交
- 回到顶部按钮
- 滚动动画
- 信任徽章条
- 信任徽章动画
- 客户评价轮播
- SG推荐码页脚
"""

from __future__ import annotations

import logging
import os
from typing import Any

from core.backends.base import TemplateBackend

logger = logging.getLogger("site-builder.template.jinja2")

try:
    from jinja2 import Environment, BaseLoader, TemplateNotFound
    _JINJA2_AVAILABLE = True
except ImportError:
    _JINJA2_AVAILABLE = False

# ═══════════════════════════════════════════════════════════
#  公共交互 JS(注入所有模板)
# ═══════════════════════════════════════════════════════════

_COMMON_JS = """
<script>
(function(){
'use strict';
// ── 平滑滚动 ──
document.querySelectorAll('a[href^="#"]').forEach(function(a){
  a.addEventListener('click',function(e){
    var id=this.getAttribute('href').slice(1);
    if(!id)return;
    var el=document.getElementById(id);
    if(el){e.preventDefault();el.scrollIntoView({behavior:'smooth',block:'start'});}
  });
});
// ── FAQ 手风琴 ──
document.querySelectorAll('.faq-item').forEach(function(item){
  var h3=item.querySelector('h3');
  var p=item.querySelector('p');
  if(h3&&p){
    p.style.maxHeight='0';p.style.overflow='hidden';p.style.transition='max-height .3s ease';
    h3.style.cursor='pointer';
    h3.insertAdjacentHTML('beforeend','<span class="faq-arrow" style="float:right;transition:transform .3s;font-size:12px;opacity:.5">▼</span>');
    item.classList.add('faq-closed');
    h3.addEventListener('click',function(){
      var open=item.classList.contains('faq-open');
      // 关闭同组其他
      item.parentElement.querySelectorAll('.faq-item').forEach(function(sib){
        sib.classList.remove('faq-open');sib.classList.add('faq-closed');
        var sp=sib.querySelector('p');if(sp)sp.style.maxHeight='0';
        var ar=sib.querySelector('.faq-arrow');if(ar)ar.style.transform='';
      });
      if(!open){item.classList.remove('faq-closed');item.classList.add('faq-open');p.style.maxHeight=p.scrollHeight+'px';var ar=item.querySelector('.faq-arrow');if(ar)ar.style.transform='rotate(90deg)';}
    });
  }
});
// ── 滚动动画 ──
var animEls=document.querySelectorAll('.feature-card,.card,.plan-card,.product-card,.article-card,.testimonial-card,.about-content,.faq-item');
if('IntersectionObserver' in window){
  var obs=new IntersectionObserver(function(entries){
    entries.forEach(function(en){
      if(en.isIntersecting){en.target.style.opacity='1';en.target.style.transform='translateY(0)';obs.unobserve(en.target);}
    });
  },{threshold:0.1});
  animEls.forEach(function(el){el.style.opacity='0';el.style.transform='translateY(30px)';el.style.transition='opacity .6s ease,transform .6s ease';obs.observe(el);});
}
// ── 回到顶部 ──
var topBtn=document.createElement('button');
topBtn.innerHTML='↑';topBtn.className='back-to-top';
topBtn.setAttribute('aria-label','回到顶部');
document.body.appendChild(topBtn);
topBtn.addEventListener('click',function(){window.scrollTo({top:0,behavior:'smooth'});});
window.addEventListener('scroll',function(){topBtn.classList.toggle('show',window.scrollY>400);});
// ── CTA 表单处理已统一到 _ctaSubmit ──
// ── 导航栏滚动变色 ──
var nav=document.getElementById('mainNav');
if(nav){
  window.addEventListener('scroll',function(){nav.classList.toggle('scrolled',window.scrollY>60);});
  nav.classList.toggle('scrolled',window.scrollY>60);
}
// ── 滚动淡入动画 (IntersectionObserver) ──
var revealEls=document.querySelectorAll('.reveal');
if('IntersectionObserver' in window && revealEls.length){
  var revealObs=new IntersectionObserver(function(entries){
    entries.forEach(function(en){
      if(en.isIntersecting){en.target.classList.add('visible');revealObs.unobserve(en.target);}
    });
  },{threshold:0.12,rootMargin:'0px 0px -40px 0px'});
  revealEls.forEach(function(el){revealObs.observe(el);});
} else {
  revealEls.forEach(function(el){el.classList.add('visible');});
}
// ── CTA 表单提交 ──
window._ctaSubmit=function(form){
  var btn=form.querySelector('button');
  if(btn){btn.textContent='\u63d0\u4ea4\u4e2d...';btn.disabled=true;}
  form.querySelectorAll('input,textarea').forEach(function(i){i.disabled=true;});
  setTimeout(function(){
    var d=document.createElement('div');d.className='cta-success';
    d.innerHTML='<div class="icon">\u2713</div><h3>\u63d0\u4ea4\u6210\u529f\uff01</h3><p>\u6211\u4eec\u5c06\u572830\u5206\u949f\u5185\u8054\u7cfb\u60a8</p>';
    form.parentElement.replaceChild(d,form);
  },800);
};
// ── CTA表单:addEventListener替代内联onsubmit ──
document.querySelectorAll('.cta-form-card, .cta-form').forEach(function(f){
  f.addEventListener('submit',function(e){e.preventDefault();window._ctaSubmit(this);});
});
// ── 汉堡菜单:addEventListener替代内联onclick ──
document.querySelectorAll('.nav-toggle').forEach(function(btn){
  btn.addEventListener('click',function(){
    this.classList.toggle('open');
    this.nextElementSibling.classList.toggle('open');
    this.setAttribute('aria-expanded',this.classList.contains('open'));
  });
});
// ── 版权年份动态注入 ──
var yrEl=document.getElementById('_yr');
if(yrEl)yrEl.textContent=new Date().getFullYear();
})();
</script>
"""

# 公共 CSS 补充
_COMMON_CSS = """
/* ── FAQ ── */
.faq-item{cursor:pointer;transition:box-shadow .2s}
.faq-item:hover{box-shadow:0 2px 12px rgba(0,0,0,.08)}
.faq-closed p{display:none}
/* ── 回到顶部 ── */
.back-to-top{position:fixed;bottom:30px;right:30px;width:44px;height:44px;border-radius:50%;background:var(--c-primary);color:var(--c-bg-white);border:none;font-size:20px;cursor:pointer;opacity:0;transform:translateY(20px);transition:all .3s;z-index:999;box-shadow:0 2px 12px rgba(0,0,0,.2)}
.back-to-top.show{opacity:1;transform:translateY(0)}
.back-to-top:hover{transform:translateY(-3px);box-shadow:0 4px 16px rgba(0,0,0,.3)}
/* (sg-powered样式已在_COMMON_CSS中定义) */
"""

# ═══════════════════════════════════════════════════════════
#  着陆页模板
# ═══════════════════════════════════════════════════════════

_LANDING_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ meta_title }}</title>
    <meta name="description" content="{{ meta_description }}">
    <meta name="keywords" content="{{ meta_keywords }}">
    <meta name="robots" content="index, follow">
    {% if canonical_url %}<link rel="canonical" href="{{ canonical_url }}">{% endif %}
    <meta property="og:title" content="{{ meta_title }}">
    <meta property="og:description" content="{{ meta_description }}">
    <meta name="twitter:card" content="summary_large_image">
    {% if og_image %}
    <meta property="og:image" content="{{ og_image | safe }}">
    {% endif %}
    <meta property="og:type" content="website">
    <meta property="og:url" content="{{ canonical_url }}">
    <style>
/* ══════════════════════════════════════════════════════════
   SG智能建站 Landing 模板 — 2025 旗舰设计系统
   ══════════════════════════════════════════════════════════ */
:root {
  --c-primary: {{ primary_color }};
  --c-primary-dark: {{ primary_dark }};
  --c-primary-light: {{ primary_light }};
  --c-primary-glass: rgba({{ primary_color | replace('#','') | batch(2) | map('join') | join(',') }}, .12);
  --c-surface: rgba(255,255,255,.72);
  --c-surface-hover: rgba(255,255,255,.92);
  --gradient-hero: linear-gradient(135deg, var(--c-primary) 0%, var(--c-primary-dark) 50%, color-mix(in srgb, var(--c-primary-dark) 70%, #000) 100%);
  --gradient-card: linear-gradient(135deg, var(--c-surface) 0%, rgba(255,255,255,.48) 100%);
  --c-text: #111827;
  --c-text-secondary: #4b5563;
  --c-text-muted: #9ca3af;
  --c-bg: #f8fafc;
  --c-bg-white: #ffffff;
  --c-border: #e5e7eb;
  --c-accent: #f59e0b;
  --c-footer-bg: {{ footer_bg }};
  --c-footer-text: {{ footer_color }};
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 20px;
  --radius-xl: 28px;
  --radius-btn: {{ radius_btn }};
  --shadow-sm: 0 1px 2px rgba(0,0,0,.04);
  --shadow-md: 0 4px 16px rgba(0,0,0,.06), 0 1px 4px rgba(0,0,0,.04);
  --shadow-lg: 0 12px 40px rgba(0,0,0,.08), 0 4px 12px rgba(0,0,0,.04);
  --shadow-xl: 0 24px 56px rgba(0,0,0,.1), 0 8px 20px rgba(0,0,0,.06);
  --shadow-primary: 0 8px 32px rgba(0,0,0,.2);
  --shadow-glow: 0 0 40px rgba(0,0,0,0) var(--c-primary);
  --transition-fast: .15s ease;
  --transition-base: .3s cubic-bezier(.4,0,.2,1);
  --transition-slow: .5s cubic-bezier(.4,0,.2,1);
  --font-sans: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --max-width: 1200px;
  --fs-display: clamp(40px, 6vw, 72px);
  --fs-h1: clamp(32px, 4.5vw, 56px);
  --fs-h2: clamp(26px, 3.5vw, 40px);
  --fs-h3: clamp(18px, 2vw, 22px);
  --fs-body: 16px;
  --fs-small: 14px;
  --fs-xs: 12px;
}
/* prefers-reduced-motion */
@media(prefers-reduced-motion:reduce) {
  *, *::before, *::after { animation-duration:.01ms!important; transition-duration:.01ms!important }
  .reveal { opacity:1!important; transform:none!important }
}
/* Focus - accessibility */
a:focus-visible, button:focus-visible, input:focus-visible, textarea:focus-visible, select:focus-visible {
  outline:2px solid var(--c-primary); outline-offset:3px; border-radius:4px;
}

/* ── Global Reset ── */
*, *::before, *::after { margin:0; padding:0; box-sizing:border-box }
html { scroll-behavior:smooth; -webkit-font-smoothing:antialiased; -moz-osx-font-smoothing:grayscale }
body { font-family:var(--font-sans); color:var(--c-text); line-height:1.7; background:var(--c-bg); overflow-x:hidden; font-size:var(--fs-body) }
img { max-width:100%; height:auto; display:block; object-fit:cover }
/* ── Safety Net: AI内容溢出防护 ── */
p, h1, h2, h3, h4, h5, h6, li, td, th, span, a, div { overflow-wrap:break-word; word-break:break-word }
table { width:100%; table-layout:fixed }
img[data-fallback] { min-height:120px; background:var(--c-bg); display:flex; align-items:center; justify-content:center }
img::after { content:''; display:none } /* CSS-only broken image fallback handled by onerror */
a { color:var(--c-primary); text-decoration:none; transition:color var(--transition-fast) }
button { font-family:inherit }

/* ── Container ── */
.container { max-width:var(--max-width); margin:0 auto; padding:0 24px }

/* ── Nav: Frosted Glass ── */
nav {
  position:fixed; top:0; left:0; right:0; z-index:1000;
  height:72px; display:flex; align-items:center;
  background:transparent; transition:all .4s cubic-bezier(.4,0,.2,1);
}
nav.scrolled {
  background:rgba(255,255,255,.82);
  backdrop-filter:blur(20px) saturate(1.8);
  -webkit-backdrop-filter:blur(20px) saturate(1.8);
  box-shadow:0 1px 24px rgba(0,0,0,.06);
}
nav .container { display:flex; align-items:center; justify-content:space-between; width:100% }
nav .logo { font-size:22px; font-weight:800; color:var(--c-bg-white); text-decoration:none; letter-spacing:-.5px; transition:color var(--transition-base) }
nav .logo .logo-dot { display:inline-block; width:10px; height:10px; border-radius:50%; background:var(--c-accent); margin-right:8px; vertical-align:middle; box-shadow:0 0 12px var(--c-accent); transition:background var(--transition-base) }
nav.scrolled .logo { color:var(--c-primary) }
nav .nav-right { display:flex; align-items:center; gap:32px }
nav .links { display:flex; gap:32px; align-items:center }
.nav-toggle { display:none; background:none; border:none; cursor:pointer; padding:8px }
.nav-toggle span { display:block; width:22px; height:2px; background:currentColor; margin:5px 0; border-radius:2px; transition:all .3s }
.nav-toggle.open span:nth-child(1) { transform:rotate(45deg) translate(5px,5px) }
.nav-toggle.open span:nth-child(2) { opacity:0 }
.nav-toggle.open span:nth-child(3) { transform:rotate(-45deg) translate(5px,-5px) }
@media(max-width:768px) {
  .nav-toggle { display:block }
  nav .links { display:none; flex-direction:column; position:absolute; top:100%; left:0; right:0; background:var(--c-bg-white); padding:20px 24px; box-shadow:var(--shadow-xl); z-index:100; border-radius:0 0 var(--radius-lg) var(--radius-lg) }
  nav .links.open { display:flex }
  nav .links a { padding:14px 0; border-bottom:1px solid var(--c-border); font-size:16px }
  nav .nav-cta { display:none }
}
nav .links a { text-decoration:none; color:rgba(255,255,255,.88); font-size:14px; font-weight:500; transition:color var(--transition-fast); position:relative }
nav .links a::after { content:''; position:absolute; bottom:-4px; left:0; width:0; height:2px; background:var(--c-bg-white); border-radius:1px; transition:width var(--transition-base) }
nav .links a:hover::after { width:100% }
nav.scrolled .links a { color:var(--c-text-secondary) }
nav.scrolled .links a::after { background:var(--c-primary) }
nav.scrolled .links a:hover { color:var(--c-primary) }
nav .nav-cta {
  display:inline-flex; align-items:center; gap:6px;
  padding:10px 28px; border-radius:var(--radius-btn);
  background:var(--c-bg-white); color:var(--c-primary); font-weight:700; font-size:14px;
  text-decoration:none; transition:all var(--transition-base);
  box-shadow:0 2px 16px rgba(0,0,0,.12);
}
nav .nav-cta:hover { transform:translateY(-1px) scale(1.02); box-shadow:0 4px 24px rgba(0,0,0,.18) }
nav .nav-cta:active { transform:scale(.97) }
nav.scrolled .nav-cta { background:var(--c-primary); color:var(--c-bg-white); box-shadow:0 4px 16px rgba(0,0,0,.15) }

/* ── Hero: Gradient Mesh + Particles ── */
.hero {
  position:relative; overflow:hidden;
  background:var(--gradient-hero);
  color:var(--c-bg-white); padding:170px 0 100px; text-align:center;
  min-height:85vh; display:flex; align-items:center;
}
/* Mesh layers */
.hero::before {
  content:''; position:absolute; inset:0;
  background:
    radial-gradient(ellipse 80% 60% at 20% 30%, rgba(255,255,255,.12) 0%, transparent 60%),
    radial-gradient(ellipse 60% 80% at 80% 70%, rgba(255,255,255,.06) 0%, transparent 50%),
    radial-gradient(ellipse 50% 50% at 60% 20%, rgba(255,200,50,.08) 0%, transparent 50%);
  pointer-events:none;
}
/* Floating orbs */
.hero-orb-1, .hero-orb-2, .hero-orb-3 {
  position:absolute; border-radius:50%; pointer-events:none;
}
.hero-orb-1 { width:500px; height:500px; top:-180px; right:-120px; background:radial-gradient(circle, rgba(255,255,255,.1) 0%, transparent 70%); animation:orbFloat 12s ease-in-out infinite }
.hero-orb-2 { width:350px; height:350px; bottom:-100px; left:-80px; background:radial-gradient(circle, rgba(255,255,255,.06) 0%, transparent 70%); animation:orbFloat 16s ease-in-out infinite reverse }
.hero-orb-3 { width:200px; height:200px; top:30%; left:15%; background:radial-gradient(circle, rgba(255,200,50,.06) 0%, transparent 70%); animation:orbFloat 10s ease-in-out infinite 2s }
@keyframes orbFloat {
  0%,100% { transform:translate(0,0) scale(1) }
  33% { transform:translate(20px,-30px) scale(1.05) }
  66% { transform:translate(-15px,20px) scale(.97) }
}
.hero-bg-img { position:absolute; inset:0; background-size:cover; background-position:center; opacity:.12; transition:opacity .6s }
.hero:hover .hero-bg-img { opacity:.18 }
.hero-glow { position:absolute; top:-200px; right:-100px; width:600px; height:600px; border-radius:50%; background:radial-gradient(circle, rgba(255,255,255,.08) 0%, transparent 70%); pointer-events:none }
.hero-illustration { position:absolute; right:5%; bottom:0; width:320px; height:260px; opacity:.12; pointer-events:none }
@media(max-width:1024px) { .hero-illustration { display:none } .about-layout { grid-template-columns:1fr } }
.hero .container { position:relative; z-index:2 }
.hero h1 { font-size:var(--fs-display); font-weight:900; margin-bottom:20px; letter-spacing:-.02em; line-height:1.1; animation:heroFadeIn .9s cubic-bezier(.4,0,.2,1) }
.hero .hero-sub { font-size:clamp(17px,2.2vw,21px); opacity:.92; margin-bottom:40px; max-width:660px; margin-left:auto; margin-right:auto; line-height:1.7; font-weight:400; animation:heroFadeIn .9s cubic-bezier(.4,0,.2,1) .12s both }
@keyframes heroFadeIn { from{opacity:0;transform:translateY(28px)} to{opacity:1;transform:translateY(0)} }

/* CTA Buttons */
.hero-btns { display:flex; gap:16px; justify-content:center; flex-wrap:wrap; animation:heroFadeIn .9s cubic-bezier(.4,0,.2,1) .24s both }
/* Primary CTA: Shimmer sweep */
@keyframes shimmer { 0%{background-position:-200% 0} 100%{background-position:200% 0} }
.hero .cta-primary {
  display:inline-flex; align-items:center; gap:10px;
  padding:18px 44px; border-radius:var(--radius-btn);
  background:var(--c-bg-white); color:var(--c-primary); font-weight:800; font-size:17px;
  text-decoration:none; transition:all var(--transition-base);
  box-shadow:var(--shadow-primary);
  position:relative; overflow:hidden;
  background-size:200% 100%;
  background-image:linear-gradient(110deg, transparent 33%, rgba(255,255,255,.35) 50%, transparent 67%);
  animation:shimmer 4s ease-in-out infinite;
}
.cta-primary:hover { transform:translateY(-3px) scale(1.02); box-shadow:0 12px 40px rgba(0,0,0,.25) }
.cta-primary:active { transform:translateY(0) scale(.97) }
.hero .cta-secondary {
  display:inline-flex; align-items:center; gap:8px;
  padding:18px 36px; border-radius:var(--radius-btn);
  background:rgba(255,255,255,.1); color:var(--c-bg-white); font-weight:600; font-size:16px;
  text-decoration:none; border:1.5px solid rgba(255,255,255,.25);
  transition:all var(--transition-base); backdrop-filter:blur(8px);
}
.hero .cta-secondary:hover { background:rgba(255,255,255,.2); transform:translateY(-2px); border-color:rgba(255,255,255,.4) }
.hero-phone-btn svg { transition:transform .3s }
.hero-phone-btn:hover svg { transform:rotate(8deg) }

/* Hero Stats: Glassmorphism cards */
.hero-stats {
  display:flex; justify-content:center; gap:20px; margin-top:52px;
  animation:heroFadeIn .9s cubic-bezier(.4,0,.2,1) .36s both; flex-wrap:wrap;
}
.hero-stat {
  text-align:center;
  background:rgba(255,255,255,.1); backdrop-filter:blur(16px);
  -webkit-backdrop-filter:blur(16px);
  padding:20px 28px; border-radius:var(--radius-lg);
  border:1px solid rgba(255,255,255,.15);
  min-width:130px; transition:all var(--transition-base);
}
.hero-stat:hover { background:rgba(255,255,255,.16); transform:translateY(-2px) }
.hero-stat .num { font-size:40px; font-weight:900; line-height:1; letter-spacing:-.02em }
.hero-stat .label { font-size:var(--fs-xs); opacity:.7; margin-top:6px; font-weight:500 }

/* Brand bar */
.brand-bar {
  background:rgba(255,255,255,.04); border-top:1px solid rgba(255,255,255,.06);
  padding:28px 0; text-align:center;
}
.brand-bar p { font-size:var(--fs-xs); opacity:.45; margin-bottom:14px; letter-spacing:1px; text-transform:uppercase; font-weight:500 }
.brand-bar .brands { display:flex; justify-content:center; align-items:center; gap:36px; flex-wrap:wrap; opacity:.4 }
.brand-bar .brands span { font-size:15px; font-weight:700; letter-spacing:.5px }

/* ── Features: Bento Grid ── */
.features { padding:120px 0 }
.features .section-header { text-align:center; margin-bottom:64px }
.features .section-header h2 { font-size:var(--fs-h2); font-weight:900; margin-bottom:14px; letter-spacing:-.02em }
.features .section-header .sub { color:var(--c-text-secondary); font-size:17px; max-width:560px; margin:0 auto }
/* Bento grid: first 2 cards span wider */
.features-grid {
  display:grid; grid-template-columns:repeat(2,1fr); gap:24px;
}
.features-grid .feature-card:nth-child(1),
.features-grid .feature-card:nth-child(2) {
  grid-column:span 1;
}
@media(max-width:768px) { .features-grid { grid-template-columns:1fr } }

.feature-card {
  background:var(--c-bg-white); padding:40px 36px; border-radius:var(--radius-lg);
  border:1px solid var(--c-border); transition:all var(--transition-base);
  position:relative; overflow:hidden;
  /* 3D tilt base */
  transform-style:preserve-3d; perspective:800px;
}
.feature-card::before {
  content:''; position:absolute; top:0; left:0; right:0; height:3px;
  background:linear-gradient(90deg, var(--c-primary), var(--c-primary-dark));
  transform:scaleX(0); transform-origin:left; transition:transform var(--transition-base);
}
.feature-card:hover::before { transform:scaleX(1) }
.feature-card .deco {
  position:absolute; bottom:-24px; right:-24px; width:100px; height:100px;
  background:var(--c-primary); opacity:.03; border-radius:50%;
  transition:all var(--transition-base);
}
.feature-card:hover .deco { transform:scale(1.8); opacity:.06 }
.feature-card:hover {
  transform:translateY(-8px); box-shadow:var(--shadow-lg); border-color:transparent;
}
.feature-card:active { transform:translateY(-4px) scale(.98) }
.feature-card .icon {
  width:60px; height:60px; border-radius:16px;
  background:var(--c-primary-light); display:flex; align-items:center; justify-content:center;
  margin-bottom:24px; position:relative;
  transition:all var(--transition-base);
}
.feature-card:hover .icon { transform:scale(1.1); box-shadow:0 4px 20px rgba(0,0,0,.08) }
.feature-card .icon[class*="icon-"] { background:transparent }
.feature-card .icon::after {
  content:''; position:absolute; inset:-3px; border-radius:18px;
  background:linear-gradient(135deg, var(--c-primary), var(--c-primary-dark));
  z-index:-1; opacity:0; transition:opacity var(--transition-base);
}
.feature-card:hover .icon::after { opacity:1 }
.feature-card h3 { font-size:var(--fs-h3); font-weight:800; margin-bottom:12px; color:var(--c-text) }
.feature-card p { color:var(--c-text-secondary); font-size:15px; line-height:1.8 }
.feature-card-img {
  width:calc(100% + 72px); height:180px; object-fit:cover; border-radius:var(--radius-md) var(--radius-md) 0 0;
  margin:-40px -36px 24px -36px;
}

/* ── How it works: Step timeline ── */
.how-it-works { padding:100px 0; background:var(--c-bg-white) }
.how-it-works .section-header { text-align:center; margin-bottom:64px }
.how-it-works .section-header h2 { font-size:var(--fs-h2); font-weight:900; margin-bottom:14px }
.how-it-works .section-header .sub { color:var(--c-text-secondary); font-size:17px }
.steps { display:flex; gap:0; justify-content:center; max-width:900px; margin:0 auto; position:relative }
.step { flex:1; text-align:center; padding:0 28px; position:relative }
.step .step-num {
  width:64px; height:64px; border-radius:50%;
  background:linear-gradient(135deg, var(--c-primary), var(--c-primary-dark));
  color:var(--c-bg-white); font-size:26px; font-weight:900;
  display:flex; align-items:center; justify-content:center;
  margin:0 auto 22px; position:relative; z-index:2;
  box-shadow:0 6px 24px rgba(0,0,0,.12);
  transition:all var(--transition-base);
}
.step:hover .step-num { transform:scale(1.1); box-shadow:0 8px 32px rgba(0,0,0,.18) }
.step:not(:last-child)::after {
  content:''; position:absolute; top:32px; left:calc(50% + 32px); right:calc(-50% + 32px);
  height:2px; background:linear-gradient(90deg, var(--c-primary-light), var(--c-border)); z-index:1;
}
.step h3 { font-size:18px; font-weight:800; margin-bottom:8px }
.step p { color:var(--c-text-secondary); font-size:14px; line-height:1.7 }

/* ── About: Split layout ── */
.about { background:var(--c-bg); padding:120px 0 }
.about .section-header { text-align:center; margin-bottom:48px }
.about .section-header h2 { font-size:var(--fs-h2); font-weight:900; margin-bottom:14px }
.about-layout { display:grid; grid-template-columns:1fr 300px; gap:48px; align-items:start; max-width:1000px; margin:0 auto }
.about-left { min-width:0 }
.about-content { line-height:2; color:var(--c-text-secondary); font-size:var(--fs-body) }
.about-image { width:100%; height:220px; object-fit:cover; border-radius:var(--radius-lg); box-shadow:var(--shadow-md); margin-top:28px }
.about-side-stats { display:flex; flex-direction:column; gap:16px }
.about-stat-card {
  background:var(--c-bg-white); border-radius:var(--radius-md); padding:24px 28px;
  border-left:4px solid var(--c-primary);
  box-shadow:var(--shadow-sm);
  transition:all var(--transition-base);
}
.about-stat-card:hover { transform:translateX(4px); box-shadow:var(--shadow-md) }
.about-stat-card .num { font-size:32px; font-weight:900; color:var(--c-primary) }
.about-stat-card .label { font-size:var(--fs-xs); color:var(--c-text-muted); margin-top:4px; font-weight:500 }

/* ── Testimonials: Glassmorphism ── */
.testimonials { padding:120px 0; background:var(--c-bg-white) }
.testimonials .section-header { text-align:center; margin-bottom:64px }
.testimonials .section-header h2 { font-size:var(--fs-h2); font-weight:900; margin-bottom:14px }
.testimonials .section-header .sub { color:var(--c-text-secondary); font-size:15px }
.testimonial-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(340px,1fr)); gap:24px }
.testimonial-card {
  background:var(--c-surface); backdrop-filter:blur(20px);
  -webkit-backdrop-filter:blur(20px);
  padding:36px; border-radius:var(--radius-lg);
  border:1px solid rgba(255,255,255,.3);
  transition:all var(--transition-base);
  position:relative;
}
.testimonial-card::before {
  content:'\201C'; position:absolute; top:16px; right:24px;
  font-size:64px; line-height:1; color:var(--c-primary); opacity:.08;
  font-family:Georgia, serif; pointer-events:none;
}
.testimonial-card:hover { box-shadow:var(--shadow-lg); transform:translateY(-4px) }
.testimonial-card .avatar, .testimonial-avatar {
  width:48px; height:48px; border-radius:50%;
  background:linear-gradient(135deg, var(--c-primary), var(--c-primary-dark));
  color:var(--c-bg-white); display:flex; align-items:center; justify-content:center;
  font-size:18px; font-weight:700; flex-shrink:0; margin-right:16px;
  box-shadow:0 2px 12px rgba(0,0,0,.1);
}
.testimonial-card .stars { color:var(--c-accent); font-size:16px; margin-bottom:16px; letter-spacing:2px; user-select:none }
.testimonial-card .stars .dim { color:var(--c-border) }
.testimonial-card blockquote {
  font-size:15px; color:var(--c-text-secondary); line-height:1.9; margin-bottom:22px; font-style:normal;
  position:relative; padding-left:20px; border-left:3px solid var(--c-primary);
}
.testimonial-card .author-row { display:flex; align-items:center; gap:14px }
.testimonial-card .avatar { width:42px; height:42px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:16px; font-weight:700; color:var(--c-bg-white); flex-shrink:0 }
.testimonial-card .author-info .name { font-weight:700; font-size:14px; color:var(--c-text) }
.testimonial-card .author-info .role { font-size:var(--fs-xs); color:var(--c-text-muted) }

/* ── FAQ: Accordion ── */
.faq { padding:120px 0; background:var(--c-bg) }
.faq .section-header { text-align:center; margin-bottom:64px }
.faq .section-header h2 { font-size:var(--fs-h2); font-weight:900; margin-bottom:14px }
.faq-layout { display:grid; grid-template-columns:1fr 380px; gap:48px; max-width:1100px; margin:0 auto }
.faq-list { display:flex; flex-direction:column; gap:12px }
.faq-item {
  background:var(--c-bg-white); padding:24px 28px; border-radius:var(--radius-md);
  border:1px solid var(--c-border); transition:all var(--transition-base);
  cursor:pointer;
}
.faq-item:hover { border-color:var(--c-primary); box-shadow:var(--shadow-sm) }
.faq-item h3 {
  font-size:16px; font-weight:700; color:var(--c-text); margin-bottom:0;
  display:flex; align-items:flex-start; gap:12px;
  list-style:none;
}
.faq-item h3 .faq-num {
  display:inline-flex; align-items:center; justify-content:center;
  min-width:26px; height:26px; border-radius:8px;
  background:var(--c-primary-light); color:var(--c-primary);
  font-size:var(--fs-xs); font-weight:800; flex-shrink:0;
}
.faq-item h3 .faq-toggle {
  margin-left:auto; font-size:18px; color:var(--c-text-muted); transition:transform var(--transition-base); flex-shrink:0;
}
.faq-item.open h3 .faq-toggle { transform:rotate(45deg) }
.faq-item p {
  color:var(--c-text-secondary); font-size:14px; line-height:1.8; margin-top:14px; padding-left:38px;
  max-height:0; overflow:hidden; opacity:0;
  transition:max-height .4s cubic-bezier(.4,0,.2,1), opacity .3s ease, margin .3s ease;
}
.faq-item.open p { max-height:300px; opacity:1; margin-top:14px }
.faq-side-card {
  background:linear-gradient(135deg, var(--c-primary), var(--c-primary-dark));
  color:var(--c-bg-white); border-radius:var(--radius-lg); padding:44px 36px;
  display:flex; flex-direction:column; justify-content:center;
  height:fit-content; position:sticky; top:100px;
  box-shadow:0 8px 40px rgba(0,0,0,.15);
}
.faq-side-card h3 { font-size:26px; font-weight:800; margin-bottom:14px }
.faq-side-card p { font-size:15px; opacity:.88; margin-bottom:28px; line-height:1.7 }
.faq-side-card .side-cta {
  display:inline-block; padding:16px 36px; border-radius:var(--radius-btn);
  background:var(--c-bg-white); color:var(--c-primary); font-weight:800; font-size:15px;
  text-decoration:none; text-align:center; transition:all var(--transition-base);
  box-shadow:0 4px 16px rgba(0,0,0,.12);
}
.faq-side-card .side-cta:hover { transform:translateY(-3px); box-shadow:0 8px 28px rgba(0,0,0,.2) }
.faq-contact { text-align:center; margin-top:44px; color:var(--c-text-muted); font-size:14px }
.faq-contact a { color:var(--c-primary); font-weight:600 }

/* ── CTA: Animated Gradient ── */
.cta-section {
  position:relative; overflow:hidden;
  background:linear-gradient(135deg, var(--c-primary-dark), var(--c-primary), color-mix(in srgb, var(--c-primary) 60%, var(--c-accent)));
  background-size:200% 200%;
  animation:ctaGradient 8s ease infinite;
  color:var(--c-bg-white); padding:120px 0; text-align:center;
}
@keyframes ctaGradient {
  0%{background-position:0% 50%} 50%{background-position:100% 50%} 100%{background-position:0% 50%}
}
.cta-section::before {
  content:''; position:absolute; inset:0;
  background-image:radial-gradient(circle, rgba(255,255,255,.06) 1px, transparent 1px);
  background-size:32px 32px; pointer-events:none;
}
.cta-section .container { position:relative; z-index:2 }
.cta-section h2 { font-size:var(--fs-h2); font-weight:900; margin-bottom:18px; letter-spacing:-.02em }
.cta-section .cta-desc { font-size:19px; opacity:.92; margin-bottom:28px }
.cta-form-card {
  max-width:480px; margin:0 auto 28px; display:flex; flex-direction:column; gap:12px;
  background:rgba(255,255,255,.1); backdrop-filter:blur(16px);
  -webkit-backdrop-filter:blur(16px);
  padding:32px; border-radius:var(--radius-xl);
  border:1px solid rgba(255,255,255,.15);
}
.cta-success { text-align:center; padding:28px 0 }
.cta-success .icon { font-size:44px; margin-bottom:14px }
.cta-success h3 { font-size:22px; font-weight:800; margin-bottom:8px }
.cta-success p { font-size:14px; opacity:.8 }
.cta-form-card input, .cta-form-card textarea {
  width:100%; padding:16px 20px; border-radius:var(--radius-btn);
  border:1px solid rgba(255,255,255,.2); background:rgba(255,255,255,.08);
  color:var(--c-bg-white); font-size:15px; outline:none;
  backdrop-filter:blur(4px); transition:all var(--transition-base);
}
.cta-form-card input:focus, .cta-form-card textarea:focus { border-color:rgba(255,255,255,.5); background:rgba(255,255,255,.14) }
.cta-form-card input::placeholder, .cta-form-card textarea::placeholder { color:rgba(255,255,255,.5) }
.cta-form-card textarea { resize:vertical; min-height:60px }
.cta-form-card button {
  padding:18px 36px; border-radius:var(--radius-btn);
  background:var(--c-bg-white); color:var(--c-primary); font-weight:800; font-size:16px;
  border:none; cursor:pointer; transition:all var(--transition-base);
  box-shadow:0 4px 20px rgba(0,0,0,.12);
}
.cta-form-card button:hover { transform:translateY(-2px); box-shadow:0 8px 32px rgba(0,0,0,.2) }
.cta-form-card button:active { transform:scale(.97) }
.cta-trust-badges { display:flex; justify-content:center; gap:28px; flex-wrap:wrap; margin-top:24px }
.cta-trust-badge { display:flex; align-items:center; gap:8px; font-size:var(--fs-xs); opacity:.82; font-weight:500 }
.cta-trust-badge .icon { width:16px; height:16px; flex-shrink:0 }
.cta-trust-badge .icon svg { width:16px; height:16px; stroke:var(--c-bg-white); fill:none; stroke-width:2.5 }

/* ── Footer ── */
footer { background:var(--c-footer-bg); color:var(--c-footer-text); padding:64px 0 0 }
.footer-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:36px; text-align:left }
.footer-col h3 { font-size:15px; font-weight:800; color:var(--c-bg-white); margin-bottom:18px }
.footer-col p { font-size:var(--fs-xs); line-height:1.9; opacity:.65 }
.footer-col ul { list-style:none }
.footer-col ul li { margin-bottom:10px }
.footer-col ul li a { color:var(--c-footer-text); font-size:var(--fs-xs); opacity:.65; transition:all var(--transition-fast) }
.footer-col ul li a:hover { opacity:1; color:var(--c-bg-white) }
.footer-bottom {
  display:flex; justify-content:space-between; align-items:center;
  padding:28px 0; font-size:var(--fs-xs); opacity:.45; flex-wrap:wrap; gap:12px;
}
.footer-bottom a { color:var(--c-footer-text) }
.sg-powered { text-align:center; padding:18px 0; font-size:var(--fs-xs); opacity:.4 }
.sg-powered a { color:inherit; text-decoration:underline }
/* Free watermark */
.sg-watermark { position:fixed; bottom:24px; right:24px; z-index:9999; background:rgba(0,0,0,.75); backdrop-filter:blur(12px); color:#fff; padding:8px 18px; border-radius:24px; font-size:11px; font-weight:700; box-shadow:0 4px 20px rgba(0,0,0,.2); cursor:pointer; text-decoration:none; display:flex; align-items:center; gap:6px; transition:all var(--transition-base) }
.sg-watermark:hover { transform:scale(1.05); background:rgba(0,0,0,.85) }
.sg-watermark svg { width:14px; height:14px; fill:currentColor }
.sg-watermark-banner { background:linear-gradient(90deg,var(--c-primary),color-mix(in srgb, var(--c-primary) 50%, #6c5ce7)); color:#fff; text-align:center; padding:7px; font-size:11px; position:relative; z-index:9998 }
.sg-watermark-banner a { color:#ffd700; font-weight:700; text-decoration:underline }

/* ── Responsive ── */
@media(max-width:1024px) {
  .faq-layout { grid-template-columns:1fr; gap:36px }
  .faq-side-card { position:static }
}
@media(max-width:768px) {
  .hero { padding:140px 0 70px; min-height:auto }
  .hero-stats { gap:16px }
  .hero-stat { padding:16px 20px; min-width:110px }
  .hero-stat .num { font-size:32px }
  .steps { flex-direction:column; gap:36px }
  .step:not(:last-child)::after { display:none }
  .testimonial-grid { grid-template-columns:1fr }
  .footer-grid { grid-template-columns:1fr 1fr; gap:28px }
  .cta-form-card button { width:100% }
  .features-grid { grid-template-columns:1fr }
}
@media(max-width:480px) {
  .hero h1 { font-size:30px }
  .hero .hero-sub { font-size:15px }
  .hero-btns { flex-direction:column; align-items:center }
  .footer-grid { grid-template-columns:1fr; gap:24px }
  .brand-bar .brands { gap:16px }
}

/* ── Scroll Reveal + Stagger ── */
.reveal { opacity:0; transform:translateY(32px); transition:opacity .7s cubic-bezier(.4,0,.2,1), transform .7s cubic-bezier(.4,0,.2,1) }
.reveal.visible { opacity:1; transform:translateY(0) }

{{ extra_css | safe }}
.skip-link{position:absolute;top:-100px;left:0;background:var(--c-primary);color:var(--c-bg-white);padding:8px 16px;z-index:9999;text-decoration:none;font-size:14px;border-radius:0 0 4px 0}.skip-link:focus{top:0}</style>
</head>
<body>
<a href="#main-content" class="skip-link">跳到主要内容</a>
    <!-- ═══ 导航栏 ═══ -->
    <header>
    <nav id="mainNav" aria-label="主导航">
        <div class="container">
            <a href="/" class="logo" aria-label="{{ name }} 首页"><span class="logo-dot"></span>{{ name }}</a>
            <div class="nav-right">
                <button class="nav-toggle" aria-label="菜单" aria-expanded="false"><span></span><span></span><span></span></button>
                <div class="links" role="menubar">
                    <a href="#features" role="menuitem">{{ features_title or "特色" }}</a>
                    {% if about_summary %}<a href="#about" role="menuitem">{{ about_title or "关于" }}</a>{% endif %}
                    {% if faq %}<a href="#faq" role="menuitem">{{ faq_title or "FAQ" }}</a>{% endif %}
                    <a href="#contact" role="menuitem">联系我们</a>
                </div>
                <a href="#contact" class="nav-cta">{{ hero_cta or '联系我们' }}</a>
            </div>
        </div>
    </nav>
    </header>

    <!-- ═══ 主内容 ═══ -->
    <main id="main-content">
    <!-- ═══ Hero 区 ═══ -->
    <section class="hero" aria-label="品牌介绍">
        {% if hero_image %}<div class="hero-bg-img" style="background-image:url('{{ hero_image | safe }}')"></div>{% endif %}
        <div class="hero-glow"></div>
        <div class="hero-shape-1"></div>
        <div class="hero-shape-2"></div>
        {{ hero_illustration | safe }}
        <div class="container" style="position:relative;z-index:2">
            <h1>{% if hero_headline %}{% if hero_headline|length < 8 %}{{ name }} · {{ hero_headline }}{% else %}{{ hero_headline }}{% endif %}{% else %}{{ name }}{% endif %}</h1>
            <p class="hero-sub">{{ hero_subheadline }}</p>
            <div class="hero-btns">
                <a href="#contact" class="cta-primary">{{ hero_cta }} →</a>
                <a href="#features" class="cta-secondary">了解更多</a>
                {% if phone %}<a href="tel:{{ phone }}" class="cta-secondary hero-phone-btn"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:4px"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>{{ phone }}</a>{% endif %}
            </div>
            {# 社会证明统计条:由AI数据驱动,有数据才显示 #}
            {% if stats and stats|length > 0 %}
            <div class="hero-stats">
                {% for s in stats %}
                <div class="hero-stat"><div class="num">{{ s.value }}</div><div class="label">{{ s.label }}</div></div>
                {% endfor %}
            </div>
            {% endif %}
        </div>
        {# 合作品牌条:由AI数据驱动,有数据才显示 #}
        {% if partner_brands and partner_brands|length > 0 %}
        <div class="brand-bar">
            <p>{{ partner_heading or '合作伙伴' }}</p>
            <div class="brands">
                {% for b in partner_brands %}
                <span>{{ b }}</span>
                {% endfor %}
            </div>
        </div>
        {% endif %}
    </section>

    <!-- ═══ Features 区 ═══ -->
    <article class="features" id="features">
        <div class="container">
            <div class="section-header reveal">
                <h2>{{ features_title }}</h2>
            </div>
            <div class="features-grid">
                {% for f in features %}
                <div class="feature-card reveal"><div class="deco"></div>
                    {% if f.image %}<img class="feature-card-img" src="{{ f.image | safe }}" srcset="{{ f.image | safe }}&w=800 800w, {{ f.image | safe }}&w=400 400w" sizes="(max-width:768px) 100vw, 400px" alt="{{ f.title }}" loading="lazy">{% endif %}
                    <div class="icon icon-{{ loop.index0 % 8 + 1 }}"></div>
                    <h3>{{ f.title }}</h3>
                    <p>{{ f.description }}</p>
                </div>
                {% endfor %}
            </div>
        </div>
    </article>

    {# 流程步骤区:由AI数据驱动,有数据才显示 #}
    {% if process_steps and process_steps|length > 0 %}
    <section class="how-it-works">
        <div class="container">
            <div class="section-header reveal">
                <h2>{{ process_title or '服务流程' }}</h2>
                <p class="sub">{{ process_subtitle or '' }}</p>
            </div>
            <div class="steps reveal">
                {% for step in process_steps %}
                <div class="step">
                    <div class="step-num">{{ loop.index }}</div>
                    <h3>{{ step.title }}</h3>
                    <p>{{ step.desc }}</p>
                </div>
                {% endfor %}
            </div>
        </div>
    </section>
    {% endif %}

    <!-- ═══ 关于我们 ═══ -->
    <section class="about" id="about">
        <div class="container">
            <div class="section-header reveal">
                <h2>{{ about_title }}</h2>
            </div>
            <div class="about-layout">
                <div class="about-left">
                    <div class="about-content reveal">{{ about_content | safe }}</div>
                    {% if about_image %}<img class="about-image" src="{{ about_image | safe }}" srcset="{{ about_image | safe }}&w=800 800w, {{ about_image | safe }}&w=400 400w" sizes="(max-width:768px) 100vw, 600px" alt="{{ name }}" loading="lazy">{% endif %}
                </div>
                {% if stats and stats|length > 0 %}
                <div class="about-side-stats reveal">
                    {% for s in stats %}
                    <div class="about-stat-card">
                        <div class="num">{{ s.value }}</div>
                        <div class="label">{{ s.label }}</div>
                    </div>
                    {% endfor %}
                </div>
                {% endif %}
            </div>
        </div>
    </section>

    {% if testimonials %}
    <!-- ═══ 评价区 ═══ -->
    <section class="testimonials">
        <div class="container">
            <div class="section-header reveal">
                <h2>{{ testimonials_title }}</h2>
                <p class="sub">真实客户反馈</p>
            </div>
            {# 评价统计由AI数据驱动,不硬编码假数字 #}
            <div class="testimonial-grid">
                {% for t in testimonials %}
                <div class="testimonial-card reveal">
                    {% set rating = t.rating|float if t.rating else 4.5 %}
                    <div class="stars">
                        {% set full = rating|round(0,'floor')|int %}
                        {% for i in range(5) %}{% if i < full %}★{% else %}☆{% endif %}{% endfor %}
                        <span style="color:var(--c-text-muted);font-size:12px;margin-left:6px">{{ rating }}</span>
                    </div>
                    <blockquote>"{{ t.text }}"</blockquote>
                    <div class="author-row">
                        <div class="avatar" style="background:linear-gradient(135deg, var(--c-primary), var(--c-primary-dark))">
                            {{ t.name[0] if t.name else 'U' }}
                        </div>
                        <div class="author-info">
                            <div class="name">{{ t.name }}</div>
                            <div class="role">{{ t.role if t.role else '' }}</div>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </section>
    {% endif %}

    {% if faq %}
    <!-- ═══ FAQ 区 ═══ -->
    <section class="faq" id="faq">
        <div class="container">
            <div class="section-header reveal">
                <h2>{{ faq_title }}</h2>
            </div>
            <div class="faq-layout">
                <div class="faq-list">
                    {% for item in faq %}
                    <div class="faq-item reveal">
                        <h3><span class="faq-num">{{ loop.index }}</span>{{ item.q }}</h3>
                        <p>{{ item.a }}</p>
                    </div>
                    {% endfor %}
                </div>
                <div class="faq-side-card reveal">
                    <h3>还有疑问?</h3>
                    <p>{% if phone %}拨打 {{ phone }} 或{% endif %}在线咨询,{%- if industry == '物流运输' %}15分钟出报价{% elif industry == '医疗健康' %}专业顾问1对1解答{% elif industry == '教育' or industry == '教育培训' %}课程顾问免费规划{% else %}快速解答{% endif %}</p>
                    <a href="#contact" class="side-cta">立即咨询 →</a>
                </div>
            </div>
            <div class="faq-contact reveal">还有其他问题?<a href="#contact">联系客服</a></div>
        </div>
    </section>
    {% endif %}

    <!-- ═══ CTA 区 ═══ -->
    <section class="cta-section" id="contact">
        <div class="container">
            <h2 class="reveal">{{ cta_headline }}</h2>
            <p class="cta-desc reveal">{{ cta_subheadline }}</p>
            {# CTA 行动号召:由AI数据驱动 #}
            <form class="cta-form-card reveal" aria-label="联系表单">
                <input type="text" name="name" placeholder="您的姓名" required aria-label="姓名">
                <input type="tel" name="phone" placeholder="手机号码" required pattern="[0-9]{11}" title="请输入11位手机号" aria-label="手机号码">
                <textarea name="message" placeholder="简单描述您的需求(选填)" rows="2" aria-label="需求描述"></textarea>
                <button type="submit">{{ cta_button }}</button>
            </form>
            {% if cta_trust_badges and cta_trust_badges|length > 0 %}
            <div class="cta-trust-badges reveal">
                {% for b in cta_trust_badges %}
                <div class="cta-trust-badge"><span class="icon"><svg viewBox="0 0 24 24" fill="none" stroke="var(--c-bg-white)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{% if loop.index0 % 3 == 0 %}<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>{% elif loop.index0 % 3 == 1 %}<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>{% else %}<path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>{% endif %}</svg></span>{{ b.text }}</div>
                {% endfor %}
            </div>
            {% elif cta_guarantee %}
            <div class="cta-trust-badges reveal">
                <div class="cta-trust-badge"><span class="icon"><svg viewBox="0 0 24 24" fill="none" stroke="var(--c-bg-white)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg></span>{{ cta_guarantee }}</div>
            </div>
            {% endif %}
        </div>
    </section>

    <!-- ═══ Footer ═══ -->
    <footer>
        <div class="container">
            <div class="footer-grid">
                <div class="footer-col">
                    <h3>{{ name }}</h3>
                    <p>{{ meta_description[:100] }}</p>
                </div>
                <div class="footer-col">
                    <h3>快速导航</h3>
                    <ul>
                        <li><a href="#features">{{ features_title or '核心功能' }}</a></li>
                        {% if about_summary %}<li><a href="#about">{{ about_title or '关于我们' }}</a></li>{% endif %}
                        {% if faq %}<li><a href="#faq">{{ faq_title or '常见问题' }}</a></li>{% endif %}
                        <li><a href="#contact">联系我们</a></li>
                    </ul>
                </div>
                <div class="footer-col">
                    <h3>联系方式</h3>
                    <ul>
                        {% if phone %}<li><a href="tel:{{ phone }}"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg> {{ phone }}</a></li>{% endif %}
                        {% if email %}<li><a href="mailto:{{ email }}"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg> {{ email }}</a></li>{% endif %}
                        {% if address %}<li><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg> {{ address }}</li>{% endif %}
                        {% if not email and not phone and not address %}<li><a href="#contact">在线联系</a></li>{% endif %}
                    </ul>
                </div>
            </div>
            <div class="footer-bottom">
                <span>© <span id="_yr"></span> {{ name }} · 保留所有权利</span>
            </div>
        </div>
        {% if not is_pro %}
        <div class="sg-watermark-banner">⚡ 由 <a href="https://auto-site-builder.onrender.com?ref={{ name | replace(' ','-') }}" target="_blank" rel="noopener">SG智能建站</a> 生成 · <a href="https://auto-site-builder.onrender.com" target="_blank" rel="noopener">升级专业版去除</a></div>
        {% endif %}
        <div class="sg-powered">{% if is_pro %}由 SG智能建站 驱动{% else %}由 <a href="https://auto-site-builder.onrender.com?ref={{ name | replace(' ','-') }}" target="_blank" rel="noopener">SG智能建站</a> 强力驱动 · 免费版{% endif %}</div>
    </footer>
    </main><!-- /main -->

    <!-- JSON-LD 结构化数据 (SEO) -->
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "LocalBusiness",
      "name": "{{ name }}",
      "description": "{{ meta_description }}",
      {% if email and 'xxx' not in email and 'XX' not in email %}"email": "{{ email }}",{% endif %}
      {% if phone and 'xxx' not in phone and 'XX' not in phone %}"telephone": "{{ phone }}",{% endif %}
      {% if website %}"url": "{{ website }}",{% endif %}
      {% if address and 'XX' not in address and '某某' not in address %}"address": {"@type": "PostalAddress", "addressLocality": "{{ address }}"},{% endif %}
      "openingHours": "Mo-Fr 09:00-18:00",
      "sameAs": []
    }
    </script>
    {% if not is_pro %}
    <a class="sg-watermark" href="https://auto-site-builder.onrender.com" target="_blank" rel="noopener" title="由SG智能建站生成，升级专业版去除水印">
        <svg viewBox="0 0 24 24"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
        SG建站
    </a>
    {% endif %}
    {{ extra_js | safe }}
    <script>
    // ── Hero 数字动画 ──
    (function(){
      var statEls=document.querySelectorAll('.hero-stat .num');
      if(!statEls.length||!('IntersectionObserver' in window)) return;
      function animateNum(el){
        var text=el.textContent.trim();
        var m=text.match(/([\\d.]+)/);
        if(!m) return;
        var target=parseFloat(m[1]);
        var isFloat=text.indexOf('.')>-1;
        var prefix=text.substring(0,text.indexOf(m[1]));
        var suffix=text.substring(text.indexOf(m[1])+m[1].length);
        var dur=1500, start=null;
        function step(ts){
          if(!start) start=ts;
          var p=Math.min((ts-start)/dur,1);
          var ease=1-Math.pow(1-p,3);
          var v=target*ease;
          el.textContent=prefix+(isFloat?v.toFixed(1):Math.round(v))+suffix;
          if(p<1) requestAnimationFrame(step);
        }
        requestAnimationFrame(step);
      }
      var obs=new IntersectionObserver(function(entries){
        entries.forEach(function(en){if(en.isIntersecting){animateNum(en.target);obs.unobserve(en.target);}});
      },{threshold:0.5});
      statEls.forEach(function(el){obs.observe(el);});
    })();
    </script>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════
#  定价页模板
# ═══════════════════════════════════════════════════════════

_PRICING_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ meta_title }}</title>
    <meta name="description" content="{{ meta_description }}">
    <meta name="robots" content="index, follow">
    {% if canonical_url %}<link rel="canonical" href="{{ canonical_url }}">{% endif %}
    <meta property="og:title" content="{{ meta_title }}">
    <meta property="og:description" content="{{ meta_description }}">
    {% if og_image %}<meta property="og:image" content="{{ og_image }}">{% endif %}
    <meta property="og:type" content="website">
    <meta property="og:url" content="{{ canonical_url }}">
    <script type="application/ld+json">{"@context":"https://schema.org","@type":"LocalBusiness","name":"{{ name }}","description":"{{ meta_description }}"}{% if telephone %},"telephone":"{{ telephone }}"{% endif %}</script>
    <style>
:root {
  --cp: {{primary_color}};
  --cpd: {{primary_dark}};
  --cpl: {{primary_light}};
  --cpg: rgba({{primary_color | replace('#','') | batch(2) | map('join') | join(',') }}, .12);
  --cs: rgba(255,255,255,.72);
  --csh: rgba(255,255,255,.92);
  --gradient-hero: linear-gradient(135deg, var(--cp) 0%, var(--cpd) 50%, color-mix(in srgb, var(--cpd) 70%, #000) 100%);
  --gradient-card: linear-gradient(135deg, var(--cs) 0%, rgba(255,255,255,.48) 100%);
  --ct: #111827;
  --cts: #4b5563;
  --ctm: #9ca3af;
  --cbg: #f8fafc;
  --cbw: #ffffff;
  --cbd: #e5e7eb;
  --cac: #f59e0b;
  --cfb: {{footer_bg}};
  --cft: {{footer_color}};
  --r-sm: 8px;
  --r-md: 12px;
  --r-lg: 20px;
  --r-xl: 28px;
  --sh-sm: 0 1px 2px rgba(0,0,0,.04);
  --sh-md: 0 4px 16px rgba(0,0,0,.06), 0 1px 4px rgba(0,0,0,.04);
  --sh-lg: 0 12px 40px rgba(0,0,0,.08), 0 4px 12px rgba(0,0,0,.04);
  --sh-xl: 0 24px 56px rgba(0,0,0,.1), 0 8px 20px rgba(0,0,0,.06);
  --sh-primary: 0 8px 32px rgba(0,0,0,.2);
  --tf: .15s ease;
  --tb: .3s cubic-bezier(.4,0,.2,1);
  --ts: .5s cubic-bezier(.4,0,.2,1);
  --fs-display: clamp(40px,6vw,72px);
  --fs-h1: clamp(32px,4.5vw,56px);
  --fs-h2: clamp(26px,3.5vw,40px);
  --fs-h3: clamp(18px,2vw,22px);
  --fs-body: 16px;
  --fs-small: 14px;
  --fs-xs: 12px;
  --font-sans: "Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  --max-w: 1200px;
}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation-duration:.01ms!important;transition-duration:.01ms!important}.reveal{opacity:1!important;transform:none!important}}
a:focus-visible,button:focus-visible,input:focus-visible,textarea:focus-visible,select:focus-visible{outline:2px solid var(--cp);outline-offset:3px;border-radius:4px}
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth;-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale}
body{font-family:var(--font-sans);color:var(--ct);line-height:1.7;background:var(--cbg);overflow-x:hidden;font-size:var(--fs-body)}
img{max-width:100%;display:block}
a{color:var(--cp);text-decoration:none;transition:color var(--tf)}
button{font-family:inherit}
.container{max-width:var(--max-w);margin:0 auto;padding:0 24px}

/* ── Nav: Frosted Glass ── */
nav{position:sticky;top:0;z-index:1000;height:72px;display:flex;align-items:center;background:rgba(255,255,255,.82);backdrop-filter:blur(20px) saturate(1.8);-webkit-backdrop-filter:blur(20px) saturate(1.8);box-shadow:0 1px 24px rgba(0,0,0,.06);transition:all .4s}
nav .container{display:flex;align-items:center;justify-content:space-between;width:100%}
nav .logo{font-size:22px;font-weight:800;color:var(--cp);letter-spacing:-.5px}
.nav-toggle{display:none;background:none;border:none;cursor:pointer;padding:8px}
.nav-toggle span{display:block;width:22px;height:2px;background:var(--cts);margin:5px 0;border-radius:2px;transition:all .3s}
.nav-toggle.open span:nth-child(1){transform:rotate(45deg) translate(5px,5px)}
.nav-toggle.open span:nth-child(2){opacity:0}
.nav-toggle.open span:nth-child(3){transform:rotate(-45deg) translate(5px,-5px)}
nav .links{display:flex;gap:28px;align-items:center}
nav .links a{color:var(--cts);font-size:14px;font-weight:500;position:relative;transition:color var(--tf)}
nav .links a::after{content:'';position:absolute;bottom:-4px;left:0;width:0;height:2px;background:var(--cp);transition:width var(--tb)}
nav .links a:hover{color:var(--cp)}
nav .links a:hover::after{width:100%}
@media(max-width:768px){.nav-toggle{display:block}nav .links{display:none;flex-direction:column;position:absolute;top:100%;left:0;right:0;background:var(--cbw);padding:20px 24px;box-shadow:var(--sh-xl);z-index:100;border-radius:0 0 var(--r-lg) var(--r-lg)}nav .links.open{display:flex}nav .links a{padding:14px 0;border-bottom:1px solid var(--cbd);font-size:16px}}

/* ── Hero: Gradient Mesh ── */
.hero{position:relative;overflow:hidden;background:var(--gradient-hero);color:var(--cbw);padding:160px 0 100px;text-align:center;min-height:80vh;display:flex;align-items:center}
.hero::before{content:'';position:absolute;inset:0;background:radial-gradient(ellipse 80% 60% at 20% 30%, rgba(255,255,255,.12) 0%, transparent 60%),radial-gradient(ellipse 60% 80% at 80% 70%, rgba(255,255,255,.06) 0%, transparent 50%),radial-gradient(ellipse 50% 50% at 60% 20%, rgba(255,200,50,.08) 0%, transparent 50%);pointer-events:none}
.hero-orb-1,.hero-orb-2,.hero-orb-3{position:absolute;border-radius:50%;pointer-events:none}
.hero-orb-1{width:500px;height:500px;top:-180px;right:-120px;background:radial-gradient(circle, rgba(255,255,255,.1) 0%, transparent 70%);animation:orbFloat 12s ease-in-out infinite}
.hero-orb-2{width:350px;height:350px;bottom:-100px;left:-80px;background:radial-gradient(circle, rgba(255,255,255,.06) 0%, transparent 70%);animation:orbFloat 16s ease-in-out infinite reverse}
.hero-orb-3{width:200px;height:200px;top:30%;left:15%;background:radial-gradient(circle, rgba(255,200,50,.06) 0%, transparent 70%);animation:orbFloat 10s ease-in-out infinite 2s}
@keyframes orbFloat{0%,100%{transform:translate(0,0) scale(1)}33%{transform:translate(20px,-30px) scale(1.05)}66%{transform:translate(-15px,20px) scale(.97)}}
.hero-glow{position:absolute;top:-200px;right:-100px;width:600px;height:600px;border-radius:50%;background:radial-gradient(circle, rgba(255,255,255,.08) 0%, transparent 70%);pointer-events:none}
.hero .container{position:relative;z-index:2}
.hero h1{font-size:var(--fs-h1);font-weight:900;margin-bottom:20px;letter-spacing:-.02em;line-height:1.1;animation:heroFadeIn .9s cubic-bezier(.4,0,.2,1)}
.hero p{font-size:clamp(17px,2.2vw,21px);opacity:.92;margin-bottom:8px;line-height:1.7;font-weight:400;animation:heroFadeIn .9s cubic-bezier(.4,0,.2,1) .12s both}
@keyframes heroFadeIn{from{opacity:0;transform:translateY(28px)}to{opacity:1;transform:translateY(0)}}
.pricing-note{margin-top:20px;font-size:15px;color:rgba(255,255,255,.75);animation:heroFadeIn .9s cubic-bezier(.4,0,.2,1) .24s both}

/* ── Pricing Section ── */
.pricing-section{padding:120px 0}
.section-header{text-align:center;margin-bottom:64px}
.section-header h2{font-size:var(--fs-h2);font-weight:900;margin-bottom:14px;letter-spacing:-.02em}
.pricing-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;max-width:1060px;margin:0 auto}
@media(max-width:1024px){.pricing-grid{grid-template-columns:repeat(2,1fr);max-width:680px}}
@media(max-width:640px){.pricing-grid{grid-template-columns:1fr}}

/* Glassmorphism Pricing Cards */
.plan-card{
  background:var(--cs);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
  padding:40px 32px;border-radius:var(--r-xl);
  border:1px solid rgba(255,255,255,.3);
  box-shadow:var(--sh-lg);position:relative;overflow:hidden;
  display:flex;flex-direction:column;transition:all var(--tb);
}
.plan-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,var(--cp),var(--cpd));transform:scaleX(0);transform-origin:left;transition:transform var(--tb)}
.plan-card:hover::before{transform:scaleX(1)}
.plan-card:hover{transform:translateY(-10px);box-shadow:0 20px 60px rgba(0,0,0,.15);border-color:rgba(255,255,255,.5)}
.plan-card:active{transform:translateY(-6px) scale(.98)}

.plan-card.popular{
  background:linear-gradient(135deg, var(--cs) 0%, rgba(255,255,255,.6) 100%);
  border:2px solid transparent;transform:scale(1.03);
  box-shadow:0 24px 64px rgba(0,0,0,.14);
  z-index:2;
}
.plan-card.popular::before{transform:scaleX(1)}
.plan-card.popular::after{
  content:'';position:absolute;inset:-2px;border-radius:var(--r-xl);
  background:linear-gradient(135deg,var(--cp),var(--cpd));z-index:-1;
}
.plan-card.popular:hover{transform:scale(1.03) translateY(-10px);box-shadow:0 28px 72px rgba(0,0,0,.18)}
@media(max-width:1024px){.plan-card.popular{transform:scale(1.02)}.plan-card.popular:hover{transform:scale(1.02) translateY(-10px)}}

.plan-badge{position:absolute;top:-14px;left:50%;transform:translateX(-50%);background:linear-gradient(135deg,var(--cp),var(--cpd));color:var(--cbw);padding:6px 24px;border-radius:20px;font-size:13px;font-weight:700;white-space:nowrap;box-shadow:0 4px 16px rgba(0,0,0,.18)}

.plan-name{font-size:20px;font-weight:700;margin-bottom:12px;color:var(--ct)}
.plan-price{font-size:52px;font-weight:800;color:var(--cp);line-height:1.1;margin-bottom:4px;letter-spacing:-.02em}
.plan-price span{font-size:18px;font-weight:400;color:var(--ctm)}
.plan-divider{height:1px;background:var(--cbd);margin:24px 0}
.plan-features{list-style:none;flex:1;margin-bottom:32px}
.plan-features li{padding:9px 0;color:var(--cts);font-size:15px;display:flex;align-items:flex-start;gap:8px}
.plan-features li::before{content:"✓";color:var(--cp);font-weight:700;flex-shrink:0;margin-top:1px}

.plan-btn{
  display:block;width:100%;padding:14px;text-align:center;border-radius:var(--r-sm);
  font-weight:700;font-size:16px;border:2px solid var(--cp);color:var(--cp);
  background:var(--cbw);transition:all var(--tb);cursor:pointer;position:relative;overflow:hidden;
}
.plan-btn:hover{background:var(--cp);color:var(--cbw);transform:translateY(-2px);box-shadow:0 8px 24px rgba(0,0,0,.18)}
.plan-btn:active{transform:scale(.97)}
.plan-card.popular .plan-btn{background:var(--cp);color:var(--cbw);border-color:var(--cp)}
.plan-card.popular .plan-btn:hover{background:var(--cpd);border-color:var(--cpd);box-shadow:0 8px 28px rgba(0,0,0,.22)}

/* ── FAQ: Glassmorphism cards ── */
.faq{padding:120px 0;background:var(--cbw)}
.faq h2{text-align:center;font-size:var(--fs-h2);font-weight:800;margin-bottom:48px}
.faq-list{max-width:780px;margin:0 auto}
.faq-item{
  background:var(--cs);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);
  padding:24px 28px;margin-bottom:12px;border-radius:var(--r-md);
  border:1px solid rgba(255,255,255,.3);
  box-shadow:var(--sh-sm);transition:all var(--tb);cursor:pointer;
  position:relative;overflow:hidden;
}
.faq-item::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,var(--cp),var(--cpd));transform:scaleX(0);transform-origin:left;transition:transform var(--tb)}
.faq-item:hover::before,.faq-item.faq-open::before{transform:scaleX(1)}
.faq-item:hover{border-color:rgba(0,0,0,.06);box-shadow:var(--sh-md);transform:translateY(-2px)}
.faq-item h3{font-size:16px;font-weight:600;color:var(--ct);cursor:pointer;display:flex;align-items:center;justify-content:space-between;gap:12px}
.faq-item h3 .faq-arrow{font-size:12px;opacity:.5;transition:transform var(--tb)}
.faq-item.faq-open h3 .faq-arrow{transform:rotate(90deg)}
.faq-item p{color:var(--cts);font-size:15px;line-height:1.75;margin-top:12px}
.faq-item .faq-answer{max-height:0;overflow:hidden;opacity:0;transition:max-height .4s cubic-bezier(.4,0,.2,1),opacity .3s,margin .3s}
.faq-item.faq-open .faq-answer{max-height:300px;opacity:1;margin-top:12px}

/* ── CTA: Animated Gradient + Orb ── */
.cta{position:relative;overflow:hidden;background:linear-gradient(135deg,var(--cpd),var(--cp),color-mix(in srgb, var(--cp) 60%, var(--cac)));background-size:200% 200%;animation:ctaGradient 8s ease infinite;color:var(--cbw);padding:120px 0;text-align:center}
@keyframes ctaGradient{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
.cta::before{content:'';position:absolute;inset:0;background-image:radial-gradient(circle, rgba(255,255,255,.06) 1px, transparent 1px);background-size:32px 32px;pointer-events:none}
.cta-orb{position:absolute;border-radius:50%;pointer-events:none}
.cta-orb-1{width:400px;height:400px;top:-120px;left:-80px;background:radial-gradient(circle, rgba(255,255,255,.08) 0%, transparent 70%);animation:orbFloat 14s ease-in-out infinite}
.cta-orb-2{width:280px;height:280px;bottom:-80px;right:-60px;background:radial-gradient(circle, rgba(255,255,255,.05) 0%, transparent 70%);animation:orbFloat 18s ease-in-out infinite reverse}
.cta .container{position:relative;z-index:2}
.cta h2{font-size:var(--fs-h2);font-weight:900;margin-bottom:16px;letter-spacing:-.02em}
.cta>p{font-size:19px;opacity:.92;margin-bottom:32px}
.cta-form{max-width:480px;margin:0 auto;display:flex;flex-direction:column;gap:12px;background:rgba(255,255,255,.1);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);padding:32px;border-radius:var(--r-xl);border:1px solid rgba(255,255,255,.15)}
.cta-form input,.cta-form textarea{width:100%;padding:16px 20px;border-radius:var(--r-md);border:1px solid rgba(255,255,255,.2);background:rgba(255,255,255,.08);color:var(--cbw);font-size:15px;outline:none;backdrop-filter:blur(4px);transition:all var(--tb)}
.cta-form input:focus,.cta-form textarea:focus{border-color:rgba(255,255,255,.5);background:rgba(255,255,255,.14)}
.cta-form input::placeholder,.cta-form textarea::placeholder{color:rgba(255,255,255,.5)}
.cta-form textarea{resize:vertical;min-height:80px}
.cta-form button{padding:18px 36px;border-radius:var(--r-md);background:var(--cbw);color:var(--cp);font-weight:700;font-size:16px;border:none;cursor:pointer;box-shadow:0 4px 20px rgba(0,0,0,.12);transition:all var(--tb)}
.cta-form button:hover{transform:translateY(-3px);box-shadow:0 8px 32px rgba(0,0,0,.2)}
.cta-form button:active{transform:scale(.97)}

footer{background:var(--cfb);color:var(--cft);text-align:center;padding:64px 0 0}
footer a{color:var(--cp)}
footer p{font-size:var(--fs-xs);line-height:2}
footer ul{list-style:none;display:flex;justify-content:center;gap:28px;flex-wrap:wrap;margin-top:18px}
footer ul li a{font-size:var(--fs-xs);opacity:.65;transition:all var(--tf)}
footer ul li a:hover{opacity:1;color:var(--cbw)}
.sg-watermark-banner{background:linear-gradient(90deg,var(--cp),color-mix(in srgb, var(--cp) 50%, #6c5ce7));color:#fff;text-align:center;padding:7px;font-size:11px;position:relative;z-index:9998}
.sg-watermark-banner a{color:#ffd700;font-weight:700;text-decoration:underline}
.sg-powered{text-align:center;padding:18px 0;font-size:var(--fs-xs);opacity:.4}
.sg-powered a{color:inherit;text-decoration:underline}

.reveal{opacity:0;transform:translateY(32px);transition:opacity .7s cubic-bezier(.4,0,.2,1),transform .7s cubic-bezier(.4,0,.2,1)}
.reveal.visible{opacity:1;transform:translateY(0)}
@keyframes fiu{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:translateY(0)}}
@media(max-width:768px){.hero{padding:140px 0 70px;min-height:auto}.pricing-grid{grid-template-columns:1fr}.cta-form{padding:24px}.cta h2{font-size:28px}.faq h2{font-size:28px}}
@media(max-width:480px){.hero h1{font-size:30px}.plan-price{font-size:42px}}
{{extra_css | safe}}
.skip-link{position:absolute;top:-100px;left:0;background:var(--cp);color:var(--cbw);padding:8px 16px;z-index:9999;font-size:14px;border-radius:0 0 4px 0}.skip-link:focus{top:0}

    </style>
</head>
<body>
<a href="#main-content" class="skip-link">跳到主要内容</a>
    <header>
    <nav aria-label="主导航">
        <div class="container">
            <a href="/" class="logo" aria-label="{{ hero_title }} 首页">{{ hero_title }}</a>
            <button class="nav-toggle" aria-label="菜单" aria-expanded="false"><span></span><span></span><span></span></button>
            <div class="links">
                <a href="#pricing">定价方案</a>
                {% if faq %}<a href="#faq">常见问题</a>{% endif %}
                <a href="#contact">联系我们</a>
            </div>
        </div>
    </nav>
    </header>
    <main id="main-content">
    <section class="hero" id="pricing">
        <div class="hero-glow"></div>
        <div class="container" style="position:relative;z-index:2">
            <h1>{{ hero_title }}</h1>
            <p>{{ hero_subtitle }}</p>
            {% if pricing_note %}<p class="pricing-note">{{ pricing_note }}</p>{% endif %}
        </div>
    </section>
    <section class="pricing-section">
        <div class="container">
            <div class="section-header reveal">
                <h2>选择适合您的方案</h2>
            </div>
            <div class="pricing-grid">
                {% for p in plans %}
                <article class="plan-card reveal{% if p.popular %} popular{% endif %}">
                    {% if p.badge %}<div class="plan-badge">{{ p.badge }}</div>{% endif %}
                    <div class="plan-name">{{ p.name }}</div>
                    <div class="plan-price">{{ p.price }}<span>{{ p.period }}</span></div>
                    <div class="plan-divider"></div>
                    <ul class="plan-features">
                        {% for f in p.features %}<li>{{ f }}</li>{% endfor %}
                    </ul>
                    <a href="#contact" class="plan-btn">选择方案</a>
                </article>
                {% endfor %}
            </div>
        </div>
    </section>
    {% if faq %}
    <section class="faq" id="faq">
        <div class="container">
            <h2>常见问题</h2>
            <div class="faq-list">
                {% for item in faq %}
                <div class="faq-item">
                    <h3>{{ item.q }}<span class="faq-arrow">▼</span></h3>
                    <p>{{ item.a }}</p>
                </div>
                {% endfor %}
            </div>
        </div>
    </section>
    {% endif %}
    <section class="cta" id="contact">
        <div class="container">
            <h2>{{ cta_title }}</h2>
            <p>{{ cta_subtitle }}</p>
            <form class="cta-form" aria-label="联系表单">
                <input type="text" name="name" placeholder="您的姓名" required aria-label="姓名">
                <input type="text" name="contact" placeholder="手机号 / 邮箱" required aria-label="联系方式">
                <textarea name="message" placeholder="请描述您的需求(选填)" aria-label="需求描述"></textarea>
                <button type="submit">{{ cta_button }}</button>
            </form>
        </div>
    </section>
    <footer><p>© <span id="_yr"></span> {{ name }}</p>
    {% if not is_pro %}
        <div class="sg-watermark-banner">⚡ 由 <a href="https://auto-site-builder.onrender.com?ref={{ name | replace(' ','-') }}" target="_blank" rel="noopener">SG智能建站</a> 生成 · <a href="https://auto-site-builder.onrender.com" target="_blank" rel="noopener">升级专业版去除</a></div>
        {% endif %}
        <div class="sg-powered">{% if is_pro %}由 SG智能建站 驱动{% else %}由 <a href="https://auto-site-builder.onrender.com?ref={{ name | replace(' ','-') }}" target="_blank" rel="noopener">SG智能建站</a> 强力驱动 · 免费版{% endif %}</div></footer>
    </main>
    {{ extra_js | safe }}
</body>
</html>"""
_SITE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ meta_title }}</title>
    <meta name="description" content="{{ meta_description }}">
    <meta name="robots" content="index, follow">
    {% if canonical_url %}<link rel="canonical" href="{{ canonical_url }}">{% endif %}
    <meta property="og:title" content="{{ meta_title }}">
    <meta property="og:description" content="{{ meta_description }}">
    {% if og_image %}<meta property="og:image" content="{{ og_image }}">{% endif %}
    <meta property="og:type" content="website">
    <meta property="og:url" content="{{ canonical_url }}">
    <script type="application/ld+json">{"@context":"https://schema.org","@type":"LocalBusiness","name":"{{ name }}","description":"{{ meta_description }}"}{% if telephone %},"telephone":"{{ telephone }}"{% endif %}</script>
    <style>
:root {
  --cp: {{primary_color}};
  --cpd: {{primary_dark}};
  --cpl: {{primary_light}};
  --cpg: rgba({{primary_color | replace('#','') | batch(2) | map('join') | join(',') }}, .12);
  --cs: rgba(255,255,255,.72);
  --csh: rgba(255,255,255,.92);
  --gradient-hero: linear-gradient(135deg, var(--cp) 0%, var(--cpd) 50%, color-mix(in srgb, var(--cpd) 70%, #000) 100%);
  --gradient-card: linear-gradient(135deg, var(--cs) 0%, rgba(255,255,255,.48) 100%);
  --ct: #111827;
  --cts: #4b5563;
  --ctm: #9ca3af;
  --cbg: #f8fafc;
  --cbw: #ffffff;
  --cbd: #e5e7eb;
  --cac: #f59e0b;
  --cfb: {{footer_bg}};
  --cft: {{footer_color}};
  --r-sm: 8px;
  --r-md: 12px;
  --r-lg: 20px;
  --r-xl: 28px;
  --sh-sm: 0 1px 2px rgba(0,0,0,.04);
  --sh-md: 0 4px 16px rgba(0,0,0,.06), 0 1px 4px rgba(0,0,0,.04);
  --sh-lg: 0 12px 40px rgba(0,0,0,.08), 0 4px 12px rgba(0,0,0,.04);
  --sh-xl: 0 24px 56px rgba(0,0,0,.1), 0 8px 20px rgba(0,0,0,.06);
  --sh-primary: 0 8px 32px rgba(0,0,0,.2);
  --tf: .15s ease;
  --tb: .3s cubic-bezier(.4,0,.2,1);
  --ts: .5s cubic-bezier(.4,0,.2,1);
  --fs-display: clamp(40px,6vw,72px);
  --fs-h1: clamp(32px,4.5vw,56px);
  --fs-h2: clamp(26px,3.5vw,40px);
  --fs-h3: clamp(18px,2vw,22px);
  --fs-body: 16px;
  --fs-small: 14px;
  --fs-xs: 12px;
  --font-sans: "Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  --max-w: 1200px;
}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation-duration:.01ms!important;transition-duration:.01ms!important}.reveal{opacity:1!important;transform:none!important}}
a:focus-visible,button:focus-visible,input:focus-visible,textarea:focus-visible,select:focus-visible{outline:2px solid var(--cp);outline-offset:3px;border-radius:4px}
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth;-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale}
body{font-family:var(--font-sans);color:var(--ct);line-height:1.7;background:var(--cbg);overflow-x:hidden;font-size:var(--fs-body)}
img{max-width:100%;display:block}
a{color:var(--cp);text-decoration:none;transition:color var(--tf)}
button{font-family:inherit}
.container{max-width:var(--max-w);margin:0 auto;padding:0 24px}

/* ── Nav: Frosted Glass ── */
nav{position:sticky;top:0;z-index:1000;height:72px;display:flex;align-items:center;background:rgba(255,255,255,.82);backdrop-filter:blur(20px) saturate(1.8);-webkit-backdrop-filter:blur(20px) saturate(1.8);box-shadow:0 1px 24px rgba(0,0,0,.06);transition:all .4s}
nav .container{display:flex;align-items:center;justify-content:space-between;width:100%}
nav .logo{font-size:22px;font-weight:800;color:var(--cp);letter-spacing:-.5px}
.nav-toggle{display:none;background:none;border:none;cursor:pointer;padding:8px}
.nav-toggle span{display:block;width:22px;height:2px;background:var(--cts);margin:5px 0;border-radius:2px;transition:all .3s}
.nav-toggle.open span:nth-child(1){transform:rotate(45deg) translate(5px,5px)}
.nav-toggle.open span:nth-child(2){opacity:0}
.nav-toggle.open span:nth-child(3){transform:rotate(-45deg) translate(5px,-5px)}
nav .links{display:flex;gap:28px;align-items:center}
nav .links a{color:var(--cts);font-size:14px;font-weight:500;position:relative;transition:color var(--tf)}
nav .links a::after{content:'';position:absolute;bottom:-4px;left:0;width:0;height:2px;background:var(--cp);transition:width var(--tb)}
nav .links a:hover{color:var(--cp)}
nav .links a:hover::after{width:100%}
nav .links a.active{color:var(--cp);font-weight:600}
nav .links a.active::after{width:100%}
@media(max-width:768px){.nav-toggle{display:block}nav .links{display:none;flex-direction:column;position:absolute;top:100%;left:0;right:0;background:var(--cbw);padding:20px 24px;box-shadow:var(--sh-xl);z-index:100;border-radius:0 0 var(--r-lg) var(--r-lg)}nav .links.open{display:flex}nav .links a{padding:14px 0;border-bottom:1px solid var(--cbd);font-size:16px}}

/* ── Hero: Gradient Mesh ── */
.hero{position:relative;overflow:hidden;background:var(--gradient-hero);color:var(--cbw);padding:160px 0 100px;text-align:center;min-height:80vh;display:flex;align-items:center}
.hero::before{content:'';position:absolute;inset:0;background:radial-gradient(ellipse 80% 60% at 20% 30%, rgba(255,255,255,.12) 0%, transparent 60%),radial-gradient(ellipse 60% 80% at 80% 70%, rgba(255,255,255,.06) 0%, transparent 50%),radial-gradient(ellipse 50% 50% at 60% 20%, rgba(255,200,50,.08) 0%, transparent 50%);pointer-events:none}
.hero-orb-1,.hero-orb-2,.hero-orb-3{position:absolute;border-radius:50%;pointer-events:none}
.hero-orb-1{width:500px;height:500px;top:-180px;right:-120px;background:radial-gradient(circle, rgba(255,255,255,.1) 0%, transparent 70%);animation:orbFloat 12s ease-in-out infinite}
.hero-orb-2{width:350px;height:350px;bottom:-100px;left:-80px;background:radial-gradient(circle, rgba(255,255,255,.06) 0%, transparent 70%);animation:orbFloat 16s ease-in-out infinite reverse}
.hero-orb-3{width:200px;height:200px;top:30%;left:15%;background:radial-gradient(circle, rgba(255,200,50,.06) 0%, transparent 70%);animation:orbFloat 10s ease-in-out infinite 2s}
@keyframes orbFloat{0%,100%{transform:translate(0,0) scale(1)}33%{transform:translate(20px,-30px) scale(1.05)}66%{transform:translate(-15px,20px) scale(.97)}}
.hero-glow{position:absolute;top:-200px;right:-100px;width:600px;height:600px;border-radius:50%;background:radial-gradient(circle, rgba(255,255,255,.08) 0%, transparent 70%);pointer-events:none}
.hero .container{position:relative;z-index:2}
.hero h1{font-size:var(--fs-h1);font-weight:900;margin-bottom:20px;letter-spacing:-.02em;line-height:1.1;animation:heroFadeIn .9s cubic-bezier(.4,0,.2,1)}
.hero p{font-size:clamp(17px,2.2vw,21px);opacity:.9;margin-bottom:32px;max-width:600px;margin-left:auto;margin-right:auto;line-height:1.7;font-weight:400;animation:heroFadeIn .9s cubic-bezier(.4,0,.2,1) .12s both}
@keyframes heroFadeIn{from{opacity:0;transform:translateY(28px)}to{opacity:1;transform:translateY(0)}}
.hero .cta-btn{display:inline-flex;align-items:center;gap:10px;background:var(--cbw);color:var(--cp);padding:18px 44px;border-radius:var(--r-md);font-weight:700;font-size:17px;box-shadow:var(--sh-primary);animation:heroFadeIn .9s cubic-bezier(.4,0,.2,1) .24s both;transition:all var(--tb);position:relative;overflow:hidden;background-image:linear-gradient(110deg,transparent 33%,rgba(255,255,255,.35) 50%,transparent 67%);background-size:200% 100%;animation:shimmer 4s ease-in-out infinite}
@keyframes shimmer{0%{background-position:-200% 0}100%{background-position:200% 0}}
.hero .cta-btn:hover{transform:translateY(-3px) scale(1.02);box-shadow:0 16px 48px rgba(0,0,0,.22)}
.hero .cta-btn:active{transform:translateY(0) scale(.97)}
@keyframes fiu{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:translateY(0)}}

section{padding:120px 0}
section:nth-child(even){background:var(--cbw)}
.section-header{text-align:center;margin-bottom:56px}
.section-header h2{font-size:var(--fs-h2);font-weight:900;margin-bottom:14px;letter-spacing:-.02em}
.section-header .sub{color:var(--cts);font-size:16px;max-width:560px;margin:0 auto}
.grid3{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:24px}

/* ── Cards: Glassmorphism ── */
.card{
  background:var(--cs);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
  padding:40px 28px;border-radius:var(--r-xl);
  border:1px solid rgba(255,255,255,.3);
  box-shadow:var(--sh-lg);position:relative;overflow:hidden;transition:all var(--tb);
}
.card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,var(--cp),var(--cpd));transform:scaleX(0);transform-origin:left;transition:transform var(--tb)}
.card:hover::before{transform:scaleX(1)}
.card:hover{transform:translateY(-10px);box-shadow:0 20px 56px rgba(0,0,0,.12);border-color:rgba(255,255,255,.5)}
.card:active{transform:translateY(-6px) scale(.98)}
.card h3{font-size:20px;font-weight:700;margin-bottom:12px;color:var(--ct)}
.card p{color:var(--cts);font-size:15px;line-height:1.75}

/* About */
.about-content{max-width:780px;margin:0 auto;line-height:2;color:var(--cts);font-size:16px}
.about-layout{display:grid;grid-template-columns:1fr 280px;gap:40px;align-items:start;max-width:1000px;margin:0 auto}
@media(max-width:1024px){.about-layout{grid-template-columns:1fr}}
.about-stat-card{
  background:var(--cs);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);
  border-radius:var(--r-md);padding:20px 24px;
  border-left:4px solid var(--cp);margin-bottom:16px;
  box-shadow:var(--sh-sm);transition:all var(--tb);position:relative;overflow:hidden;
}
.about-stat-card:hover{transform:translateX(6px) translateY(-2px);box-shadow:var(--sh-md)}
.about-stat-card .num{font-size:28px;font-weight:800;color:var(--cp);letter-spacing:-.02em}
.about-stat-card .label{font-size:13px;color:var(--ctm);margin-top:4px}

/* Quote */
.quote-grid,.products-grid,.articles-grid{display:grid;gap:24px}
.quote-grid{grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}
.products-grid{grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}
.articles-grid{grid-template-columns:repeat(auto-fit,minmax(300px,1fr))}

.quote-card{
  background:var(--cs);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
  padding:36px;border-radius:var(--r-xl);
  border:1px solid rgba(255,255,255,.3);
  box-shadow:var(--sh-md);position:relative;overflow:hidden;transition:all var(--tb);
}
.quote-card::before{content:'C';position:absolute;top:16px;left:24px;font-size:64px;color:var(--cp);opacity:.12;line-height:1;font-family:Georgia,serif}
.quote-card:hover{transform:translateY(-4px);box-shadow:var(--sh-lg)}
.quote-card blockquote{font-size:16px;color:var(--cts);line-height:1.8;font-style:italic;margin-bottom:16px;padding-top:36px;border-left:3px solid var(--cp);padding-left:18px}
.quote-card .author{font-weight:700;color:var(--cp);font-size:14px}

/* Product Cards */
.product-card{
  background:var(--cs);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
  padding:36px 28px;border-radius:var(--r-xl);
  border:1px solid rgba(255,255,255,.3);
  box-shadow:var(--sh-lg);text-align:center;position:relative;overflow:hidden;transition:all var(--tb);
}
.product-card:hover{transform:translateY(-10px);box-shadow:0 20px 60px rgba(0,0,0,.12);border-color:rgba(255,255,255,.5)}
.product-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,var(--cp),var(--cpd));transform:scaleX(0);transform-origin:left;transition:transform var(--tb)}
.product-card:hover::before{transform:scaleX(1)}
.product-card .badge{position:absolute;top:-12px;left:50%;transform:translateX(-50%);background:linear-gradient(135deg,var(--cp),var(--cpd));color:var(--cbw);padding:5px 20px;border-radius:12px;font-size:12px;font-weight:700;white-space:nowrap;box-shadow:0 4px 16px rgba(0,0,0,.18)}
.product-card h3{font-size:20px;font-weight:700;margin-bottom:8px;color:var(--ct)}
.product-card .price{font-size:28px;font-weight:800;color:var(--cp);margin:12px 0;letter-spacing:-.02em}
.product-card .features{color:var(--ctm);font-size:14px;margin-bottom:20px}
.product-card .plan-btn{display:inline-block;padding:12px 28px;border:2px solid var(--cp);color:var(--cp);border-radius:var(--r-md);font-weight:600;font-size:14px;transition:all var(--tb)}
.product-card .plan-btn:hover{background:var(--cp);color:var(--cbw);transform:translateY(-2px);box-shadow:0 6px 20px rgba(0,0,0,.15)}
.product-card .plan-btn:active{transform:scale(.97)}

/* Article Cards */
.article-card{
  background:var(--cs);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
  padding:28px;border-radius:var(--r-xl);
  border:1px solid rgba(255,255,255,.3);
  box-shadow:var(--sh-md);transition:all var(--tb);cursor:pointer;
  display:flex;flex-direction:column;
}
.article-card:hover{transform:translateY(-8px);box-shadow:0 16px 48px rgba(0,0,0,.1);border-color:rgba(255,255,255,.5)}
.article-card:active{transform:translateY(-4px) scale(.98)}
.article-card .tag{display:inline-block;background:var(--cpg);color:var(--cp);padding:3px 12px;border-radius:10px;font-size:12px;font-weight:600;margin-bottom:10px;width:fit-content}
.article-card .date{color:var(--ctm);font-size:13px;margin-bottom:10px}
.article-card h3{font-size:18px;font-weight:700;margin-bottom:10px;color:var(--ct);line-height:1.4}
.article-card .excerpt{color:var(--ctm);font-size:14px;line-height:1.7;flex:1}

/* ── CTA: Gradient + Orb ── */
.cta{position:relative;overflow:hidden;background:linear-gradient(135deg,var(--cpd),var(--cp),color-mix(in srgb, var(--cp) 60%, var(--cac)));background-size:200% 200%;animation:ctaGradient 8s ease infinite;color:var(--cbw);text-align:center;padding:120px 0}
@keyframes ctaGradient{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
.cta::before{content:'';position:absolute;inset:0;background-image:radial-gradient(circle, rgba(255,255,255,.06) 1px, transparent 1px);background-size:32px 32px;pointer-events:none}
.cta-orb{position:absolute;border-radius:50%;pointer-events:none}
.cta-orb-1{width:400px;height:400px;top:-120px;left:-80px;background:radial-gradient(circle, rgba(255,255,255,.08) 0%, transparent 70%);animation:orbFloat 14s ease-in-out infinite}
.cta-orb-2{width:280px;height:280px;bottom:-80px;right:-60px;background:radial-gradient(circle, rgba(255,255,255,.05) 0%, transparent 70%);animation:orbFloat 18s ease-in-out infinite reverse}
.cta .container{position:relative;z-index:2}
.cta h2{font-size:var(--fs-h2);font-weight:900;margin-bottom:16px;letter-spacing:-.02em}
.cta>p{font-size:19px;opacity:.92;margin-bottom:32px}
.cta-form{max-width:480px;margin:0 auto;display:flex;flex-direction:column;gap:12px;background:rgba(255,255,255,.1);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);padding:32px;border-radius:var(--r-xl);border:1px solid rgba(255,255,255,.15)}
.cta-form input,.cta-form textarea{width:100%;padding:16px 20px;border-radius:var(--r-md);border:1px solid rgba(255,255,255,.2);background:rgba(255,255,255,.08);color:var(--cbw);font-size:15px;outline:none;backdrop-filter:blur(4px);transition:all var(--tb)}
.cta-form input:focus,.cta-form textarea:focus{border-color:rgba(255,255,255,.5);background:rgba(255,255,255,.14)}
.cta-form input::placeholder,.cta-form textarea::placeholder{color:rgba(255,255,255,.5)}
.cta-form textarea{resize:vertical;min-height:80px}
.cta-form button{padding:18px 36px;border-radius:var(--r-md);background:var(--cbw);color:var(--cp);font-weight:700;font-size:16px;border:none;cursor:pointer;box-shadow:0 4px 20px rgba(0,0,0,.12);transition:all var(--tb)}
.cta-form button:hover{transform:translateY(-3px);box-shadow:0 8px 32px rgba(0,0,0,.2)}
.cta-form button:active{transform:scale(.97)}

footer{background:var(--cfb);color:var(--cft);text-align:center;padding:64px 0 0}
footer a{color:var(--cp)}
footer p{font-size:var(--fs-xs);line-height:2}
footer ul{list-style:none;display:flex;justify-content:center;gap:28px;flex-wrap:wrap;margin-top:18px}
footer ul li a{font-size:var(--fs-xs);opacity:.65;transition:all var(--tf)}
footer ul li a:hover{opacity:1;color:var(--cbw)}
.sg-watermark-banner{background:linear-gradient(90deg,var(--cp),color-mix(in srgb, var(--cp) 50%, #6c5ce7));color:#fff;text-align:center;padding:7px;font-size:11px;position:relative;z-index:9998}
.sg-watermark-banner a{color:#ffd700;font-weight:700;text-decoration:underline}

.reveal{opacity:0;transform:translateY(32px);transition:opacity .7s cubic-bezier(.4,0,.2,1),transform .7s cubic-bezier(.4,0,.2,1)}
.reveal.visible{opacity:1;transform:translateY(0)}
@media(prefers-reduced-motion:reduce){.reveal{transition:none}.hero h1,.hero p{animation:none}}

@media(max-width:768px){
  .hero{padding:140px 0 60px;min-height:auto}
  section{padding:64px 0}
  .section-header h2{font-size:28px}
  .grid3,.quote-grid,.products-grid,.articles-grid{grid-template-columns:1fr}
  .cta-form{padding:24px}
  .cta h2{font-size:28px}
  .cta-form button{width:100%}
}
@media(max-width:480px){
  .hero h1{font-size:30px}
  .hero p{font-size:15px}
  .hero .cta-btn{padding:14px 32px;font-size:15px}
  .footer-grid{grid-template-columns:1fr;gap:24px}
}

{{extra_css | safe}}
.skip-link{position:absolute;top:-100px;left:0;background:var(--cp);color:var(--cbw);padding:8px 16px;z-index:9999;font-size:14px;border-radius:0 0 4px 0}.skip-link:focus{top:0}

    </style>
</head>
<body>
<a href="#main-content" class="skip-link">跳到主要内容</a>
    <header>
    <nav id="mainNav" aria-label="主导航">
        <div class="container">
            <a href="/" class="logo" aria-label="{{ name }} 首页">{{ hero_headline[:10] }}</a>
            <button class="nav-toggle" aria-label="菜单" aria-expanded="false"><span></span><span></span><span></span></button>
            <div class="links">
                {% if services %}<a href="#services">{{ services_title }}</a>{% endif %}
                {% if about_summary %}<a href="#about">{{ about_title }}</a>{% endif %}
                {% if products %}<a href="#products">{{ products_title }}</a>{% endif %}
                {% if articles %}<a href="#blog">{{ blog_title }}</a>{% endif %}
                <a href="#contact">联系我们</a>
            </div>
        </div>
    </nav>
    </header>
    <main id="main-content">
    <section class="hero"><div class="hero-glow"></div><div class="container" style="position:relative;z-index:2"><h1>{{ hero_headline }}</h1><p>{{ hero_subheadline }}</p><a href="#contact" class="cta-btn">{{ hero_cta }}</a></div></section>
    {% if services %}
    <section id="services"><div class="container"><div class="section-header reveal"><h2>{{ services_title }}</h2></div><div class="grid3">{% for s in services %}<div class="card reveal"><h3>{{ s.title }}</h3><p>{{ s.description }}</p></div>{% endfor %}</div></div></section>
    {% endif %}
    {% if about_summary %}
    <section id="about"><div class="container"><div class="section-header reveal"><h2>{{ about_title }}</h2></div><div class="about-layout"><div><div class="about-content reveal">{{ about_summary | safe }}</div>{% if story_content %}<div class="about-content reveal" style="margin-top:24px">{{ story_content | safe }}</div>{% endif %}</div>{% if stats and stats|length > 0 %}<div class="reveal">{% for s in stats %}<div class="about-stat-card"><div class="num">{{ s.value }}</div><div class="label">{{ s.label }}</div></div>{% endfor %}</div>{% endif %}</div></div></section>
    {% endif %}
    {% if team %}
    <section><div class="container"><div class="section-header reveal"><h2>{{ team_title }}</h2></div><div class="grid3">{% for m in team %}<div class="card reveal"><h3>{{ m.name }}</h3><p><strong>{{ m.title }}</strong></p><p>{{ m.bio }}</p></div>{% endfor %}</div></div></section>
    {% endif %}
    {% if values %}
    <section><div class="container"><div class="section-header reveal"><h2>{{ values_title }}</h2></div><div class="grid3">{% for v in values %}<div class="card reveal"><h3>{{ v.title }}</h3><p>{{ v.description }}</p></div>{% endfor %}</div></div></section>
    {% endif %}
    {% if products %}
    <section id="products"><div class="container"><div class="section-header reveal"><h2>{{ products_title }}</h2>{% if products_subtitle %}<p class="sub">{{ products_subtitle }}</p>{% endif %}</div><div class="products-grid">{% for p in products %}<article class="product-card reveal">{% if p.badge %}<div class="badge">{{ p.badge }}</div>{% endif %}<h3>{{ p.name }}</h3><p style="color:var(--ctm);font-size:14px;margin-bottom:8px">{{ p.desc }}</p><div class="price">{{ p.price }}</div><div class="features">{% for f in p.features %}{{ f }}{% if not loop.last %} · {% endif %}{% endfor %}</div><a href="#contact" class="plan-btn">立即咨询</a></article>{% endfor %}</div></div></section>
    {% endif %}
    {% if testimonials %}
    <section><div class="container"><div class="section-header reveal"><h2>{{ testimonials_title }}</h2></div><div class="quote-grid">{% for t in testimonials %}<div class="quote-card reveal"><blockquote>"{{ t.text }}"</blockquote><div class="author">- {{ t.name }}</div></div>{% endfor %}</div></div></section>
    {% endif %}
    {% if articles %}
    <section id="blog"><div class="container"><div class="section-header reveal"><h2>{{ blog_title }}</h2>{% if blog_subtitle %}<p class="sub">{{ blog_subtitle }}</p>{% endif %}</div><div class="articles-grid">{% for a in articles %}<article class="article-card reveal"><span class="tag">{{ a.tag }}</span><div class="date">{{ a.date }}</div><h3>{{ a.title }}</h3><p class="excerpt">{{ a.excerpt }}</p></article>{% endfor %}</div></div></section>
    {% endif %}
    <section id="contact" class="cta"><div class="container"><h2>{{ cta_headline }}</h2><p>{{ cta_subheadline }}</p><form class="cta-form" aria-label="联系表单"><input type="text" name="name" placeholder="您的姓名" required aria-label="姓名"><input type="text" name="contact" placeholder="手机号 / 邮箱" required aria-label="联系方式"><textarea name="message" placeholder="请描述您的需求(选填)" aria-label="需求描述"></textarea><button type="submit">{{ cta_button }}</button></form></div></section>
    <footer><p>© <span id="_yr"></span> {{ name }}</p>
    {% if not is_pro %}
        <div class="sg-watermark-banner">⚡ 由 <a href="https://auto-site-builder.onrender.com?ref={{ name | replace(' ','-') }}" target="_blank" rel="noopener">SG智能建站</a> 生成 · <a href="https://auto-site-builder.onrender.com" target="_blank" rel="noopener">升级专业版去除</a></div>
        {% endif %}
        <div class="sg-powered">{% if is_pro %}由 SG智能建站 驱动{% else %}由 <a href="https://auto-site-builder.onrender.com?ref={{ name | replace(' ','-') }}" target="_blank" rel="noopener">SG智能建站</a> 强力驱动 · 免费版{% endif %}</div></footer>
    </main>
    {{ extra_js | safe }}
</body>
</html>"""









class Jinja2TemplateBackend(TemplateBackend):
    """
    Jinja2 模板引擎后端(SG v4.0 营收引擎版)

    优先级 10(模板渲染首选)。功能完整,支持模板继承。
    所有生成的页面均包含完整的交互功能 + 转化漏斗组件:
    - 平滑滚动导航
    - 移动端汉堡菜单
    - FAQ 手风琴折叠
    - CTA 联系表单
    - 回到顶部按钮
    - 滚动淡入动画
    - 信任徽章动画
    - 信任徽章动画
    - SG推荐码页脚(病毒式增长)
    """

    name = "jinja2"
    priority = 10

    def __init__(self, template_dir: str = ""):
        self.env = Environment(
            loader=BaseLoader(),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._builtin = {
            "landing": _LANDING_TEMPLATE,
            "pricing": _PRICING_TEMPLATE,
            "site": _SITE_TEMPLATE,
        }
        # 动态加载电商模板
        try:
            from core.backends.template.shop_template import SHOP_TEMPLATE
            self._builtin["shop"] = SHOP_TEMPLATE
        except ImportError:
            pass

    @classmethod
    def _check_dependencies(cls) -> None:
        if not _JINJA2_AVAILABLE:
            raise ImportError("jinja2 未安装: pip install jinja2")

    def _get_template(self, name: str) -> str:
        if name in self._builtin:
            return self._builtin[name]
        raise TemplateNotFound("模板 " + repr(name) + " 不存在")

    # ── 后处理:过滤假数据/禁止词 ──
    _BANNED_WORDS = ['引领', '卓越', '领先', '一站式', '全方位', '极致', '赋能', '首屈一指', '致力于', '旨在', '专业', '优质', '高端', '闭环', '矩阵', '生态', '打法', '颗粒度', '抓手', '底层逻辑', '降本增效', '协同']
    _BANNED_PHRASES = [
        ('深受', '信赖'),  # "深受XXX信赖" 搭配
        ('XX路', '号'),    # 占位符地址
        ('某某', '公司'),   # 占位符公司名
    ]

    @classmethod
    def _sanitize_html(cls, html: str) -> str:
        """后处理:移除模板层假数据、替换禁止词、XSS防护"""
        import re
        # 0. XSS防护：移除javascript:/data:text/html协议的URL
        html = re.sub(r'(href|src|action)\s*=\s*["\']\s*javascript\:', r'\1="#"', html, flags=re.IGNORECASE)
        html = re.sub(r'(href|src|action)\s*=\s*["\']\s*data\:text/html', r'\1="#"', html, flags=re.IGNORECASE)
        # 1. 移除空hero-stats(无AI数据时渲染的空壳)
        html = re.sub(r'<div class="hero-stats">\s*</div>', '', html)
        # 2. 移除空brand-bar
        html = re.sub(r'<div class="brand-bar">.*?</div>\s*</div>', '', html, flags=re.DOTALL)
        # 3. 禁止词替换
        for w in cls._BANNED_WORDS:
            html = html.replace(w, '')
        # 4. 禁止搭配替换
        for a, b in cls._BANNED_PHRASES:
            html = re.sub(f'{a}.*?{b}', f'{a}客户{b}', html)
        # 5. Remove leftover fake urgency/countdown HTML
        html = re.sub(r'<div class="urgency-strip"[^>]*>.*?</div>\s*</div>', '', html, flags=re.DOTALL)
        # 6. Remove JSON-LD fields with placeholder values (xxx/XX/某某)
        html = re.sub(r'"telephone"\s*:\s*"[^"]*[xX]{2,}[^"]*"\s*,?', '', html)
        html = re.sub(r'"addressLocality"\s*:\s*"[^"]*(?:[xX]{2}|某某)[^"]*"\s*,?', '', html)
        html = re.sub(r'"streetAddress"\s*:\s*"[^"]*(?:[xX]{2}|某某)[^"]*"\s*,?', '', html)
        html = re.sub(r'"email"\s*:\s*"[^"]*[xX]{2,}[^"]*"\s*,?', '', html)
        # Remove entire address object if still contains placeholders
        html = re.sub(r'"address"\s*:\s*\{[^}]*(?:[xX]{2}|某某)[^}]*\}\s*,?', '', html)
        # 7. Remove empty JSON-LD trailing commas
        html = re.sub(r',\s*}', '}', html)
        # 8. 外部图片死链降级：给所有<img>加onerror，加载失败时替换为SVG占位图
        img_fallback = 'this.onerror=null;this.src=&quot;data:image/svg+xml,&lt;svg xmlns=\\&quot;http://www.w3.org/2000/svg\\&quot; viewBox=\\&quot;0 0 400 200\\&quot;&gt;&lt;rect fill=\\&quot;%23f1f5f9\\&quot; width=\\&quot;400\\&quot; height=\\&quot;200\\&quot;/&gt;&lt;text x=\\&quot;50%25\\&quot; y=\\&quot;50%25\\&quot; dominant-baseline=\\&quot;middle\\&quot; text-anchor=\\&quot;middle\\&quot; fill=\\&quot;%2394a3b8\\&quot; font-size=\\&quot;16\\&quot;&gt;🖼 图片加载失败&lt;/text&gt;&lt;/svg&gt;&quot;'
        html = re.sub(r'<img(?![^>]*onerror)', '<img onerror="' + img_fallback + '"', html)
        return html

    def render(self, template: str, context: dict[str, Any]) -> str:
        tmpl = self._get_template(template)
        ctx = self._prepare_context(template, context)
        # 注入公共交互资源(CSS/JS 使用模板变量渲染主题色)
        ctx["extra_css"] = self._render_common_css(ctx)
        ctx["extra_js"] = _COMMON_JS
        jinja_tmpl = self.env.from_string(tmpl)
        html = jinja_tmpl.render(**ctx)
        return self._sanitize_html(html)

    def render_site(self, pages: dict[str, str], context: dict[str, Any]) -> dict[str, str]:
        result = {}
        ctx = self._prepare_context("site", context)
        ctx["extra_css"] = self._render_common_css(ctx)
        ctx["extra_js"] = _COMMON_JS
        for name, tmpl in pages.items():
            jinja_tmpl = self.env.from_string(tmpl)
            result[name] = self._sanitize_html(jinja_tmpl.render(**ctx))
        return result

    def _render_common_css(self, ctx: dict) -> str:
        """渲染公共CSS + 动态SVG图标CSS"""
        css = _COMMON_CSS
        pc = ctx.get("primary_color", "#1a73e8")
        css = css.replace("{{ primary_color }}", pc)
        css = css.replace("{{ primary_dark }}", ctx.get("primary_dark", "#0d47a1"))
        # Generate feature icon CSS with encoded primary color
        css += self._gen_feature_icon_css(pc)
        return css

    @staticmethod
    def _gen_feature_icon_css(color: str) -> str:
        """生成8个SVG图标背景CSS,用运行时主色编码"""
        # URL-encode the # for SVG data URI
        c = color.replace("#", "%23")
        # 8 professional line icons: bolt, shield, bar-chart, clock, check-circle, lightbulb, wrench, trending-up
        paths = [
            "M13 2L3 14h9l-1 8 10-12h-9l1-8z",  # bolt
            "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z",  # shield
            "M18 20V10M12 20V4M6 20v-6",  # bar-chart
            "M12 2a10 10 0 100 20 10 10 0 000-20zM12 6v6l4 2",  # clock
            "M22 11.08V12a10 10 0 11-5.93-9.14",  # check-circle outline
            "M12 2v1m0 17v1M4.93 4.93l.7.7m12.74 12.74l.7.7M2 12h1m17 0h1M4.93 19.07l.7-.7m12.74-12.74l.7-.7",  # lightbulb rays
            "M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z",  # wrench
            "M23 6l-9.5 9.5-5-5L1 18",  # trending-up
        ]
        check_path = "M22 11.08V12a10 10 0 11-5.93-9.14M22 4L12 14.01l-3-3"  # check-circle with checkmark
        paths[4] = check_path  # replace #5 with full check-circle
        lines = []
        for i, p in enumerate(paths):
            svg = f"%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='{c}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='{p}'/%3E%3C/svg%3E"
            lines.append(f".feature-card .icon-{i+1} {{background-image:url(\"data:image/svg+xml,{svg}\");background-repeat:no-repeat;background-position:center;background-size:28px}}")
        return "\n".join(lines)

    def _prepare_context(self, template_name: str, context: dict) -> dict:
        ctx = dict(context)
        # ── 行业色彩自适应 ──
        _INDUSTRY_COLORS = {
            "物流运输": {"primary": "#0d7c3e", "dark": "#085a2b", "light": "#e6f7ed"},
            "教育": {"primary": "#7c3aed", "dark": "#5b21b6", "light": "#ede9fe"},
            "教育培训": {"primary": "#7c3aed", "dark": "#5b21b6", "light": "#ede9fe"},
            "科技": {"primary": "#1d4ed8", "dark": "#1e3a8a", "light": "#dbeafe"},
            "科技软件": {"primary": "#1d4ed8", "dark": "#1e3a8a", "light": "#dbeafe"},
            "医疗健康": {"primary": "#059669", "dark": "#047857", "light": "#d1fae5"},
            "餐饮美食": {"primary": "#dc2626", "dark": "#991b1b", "light": "#fee2e2"},
            "房地产": {"primary": "#b45309", "dark": "#92400e", "light": "#fef3c7"},
            "房产建筑": {"primary": "#b45309", "dark": "#92400e", "light": "#fef3c7"},
            "金融保险": {"primary": "#1d4ed8", "dark": "#1e3a8a", "light": "#dbeafe"},
            "美容美发": {"primary": "#db2777", "dark": "#9d174d", "light": "#fce7f3"},
            "法律咨询": {"primary": "#374151", "dark": "#1f2937", "light": "#f3f4f6"},
            "法律服务": {"primary": "#374151", "dark": "#1f2937", "light": "#f3f4f6"},
            "装修建材": {"primary": "#d97706", "dark": "#92400e", "light": "#fef3c7"},
            "汽车服务": {"primary": "#2563eb", "dark": "#1e40af", "light": "#dbeafe"},
            "旅游酒店": {"primary": "#0891b2", "dark": "#0e7490", "light": "#cffafe"},
            "健身运动": {"primary": "#e11d48", "dark": "#be123c", "light": "#ffe4e6"},
        }
        _ic = _INDUSTRY_COLORS.get(ctx.get("industry", ""), None)
        # 行业颜色映射优先（用户指定行业时应该用对应主题色），仅无映射时才用AI返回的primary_color
        if _ic is None:
            # 无行业映射，使用AI返回的primary_color或默认蓝
            if ctx.get("primary_color") and ctx["primary_color"].startswith("#"):
                import colorsys
                try:
                    r,g,b = int(ctx["primary_color"][1:3],16)/255, int(ctx["primary_color"][3:5],16)/255, int(ctx["primary_color"][5:7],16)/255
                    h,l,s = colorsys.rgb_to_hls(r,g,b)
                    _ic = {
                        "primary": ctx["primary_color"],
                        "dark": "#{:02x}{:02x}{:02x}".format(*(int(c*255) for c in colorsys.hls_to_rgb(h, max(0, l-0.12), s))),
                        "light": "#{:02x}{:02x}{:02x}".format(*(int(c*255) for c in colorsys.hls_to_rgb(h, min(1, l+0.38), max(0, s-0.3)))),
                    }
                except Exception:
                    _ic = {"primary": "#1a73e8", "dark": "#0d47a1", "light": "#e8f0fe"}
            else:
                _ic = {"primary": "#1a73e8", "dark": "#0d47a1", "light": "#e8f0fe"}
        # 行业映射命中时覆盖AI返回的颜色
        ctx["primary_color"] = _ic["primary"]
        ctx["primary_dark"] = _ic["dark"]
        ctx["primary_light"] = _ic["light"]
        ctx.setdefault("radius_btn", "8px")
        ctx.setdefault("footer_bg", "#1a1a2e")
        ctx.setdefault("footer_color", "#ccc")
        ctx.setdefault("footer_text", "")
        ctx.setdefault("email", "")
        ctx.setdefault("phone", "")
        ctx.setdefault("address", "")
        # canonical: 用环境变量BASE_URL构造,确保SEO规范
        base_url = os.environ.get("BASE_URL", "https://auto-site-builder.onrender.com")
        if not ctx.get("canonical_url"):
            ctx["canonical_url"] = base_url
        ctx.setdefault("extra_css", "")
        ctx.setdefault("extra_js", "")
        ctx.setdefault("name", "")
        ctx.setdefault("industry", "")
        ctx.setdefault("og_image", "")
        ctx.setdefault("meta_title", ctx.get("name", "") + (" - " + ctx.get("description", "") if ctx.get("description") else ""))
        # Strengthen short meta_title (<30c)
        mt = ctx.get("meta_title", "")
        if len(mt) < 30:
            ind = ctx.get("industry", "")
            # 策略：追加行业+CTA后缀而非完全替换，保留原有语义
            suffix = ""
            if ind and ind not in mt:
                suffix = f" | {ind}"
            # 根据行业选择合适的CTA后缀，避免硬编码"免费试用"
            _cta_suffixes = {
                "医疗": " | 预约咨询", "健康": " | 预约咨询",
                "教育": " | 免费试听", "培训": " | 免费试听",
                "法律": " | 免费咨询", "金融": " | 专业顾问",
                "餐饮": " | 在线订餐", "外卖": " | 在线订餐",
            }
            _ind = ctx.get("industry", "")
            _matched_cta = None
            for _key, _cta in _cta_suffixes.items():
                if _key in _ind:
                    _matched_cta = _cta
                    break
            if not _matched_cta:
                if "免费" not in mt and "试用" not in mt:
                    _matched_cta = " | 在线体验"
                else:
                    _matched_cta = ""
            if _matched_cta:
                suffix += _matched_cta
            new_title = mt.rstrip() + suffix
            if len(new_title) > len(mt):
                ctx["meta_title"] = new_title
        desc = ctx.get('description', '')
        # name: 优先用name字段,hero_headline常含"欢迎来到"等无关前缀不宜做品牌名
        raw_name = ctx.get('name', '')
        if raw_name:
            name = raw_name
        else:
            hh = ctx.get('hero_headline', '')
            # 从hero_headline提取品牌名:取'·'或'-'前部分,并去掉常见前缀
            name = hh.split('·')[0].split('-')[0].strip()
            for prefix in ('欢迎来到', '欢迎了解', '遇见', '发现'):
                if name.startswith(prefix):
                    name = name[len(prefix):].strip()
            if not name:
                name = '我们'
        ind = ctx.get('industry', '')
        if not desc:
            parts = []
            if name and ind:
                parts.append(f"{name}是{ind}领域专业服务商")
            elif ind:
                parts.append(f"专业{ind}服务商")
            elif name:
                parts.append(f"{name}为您提供专业服务")
            else:
                parts.append("专业服务商")
            parts.append("提供一站式解决方案,多年行业经验,值得信赖的合作伙伴")
            desc = ",".join(parts) + "。"
        elif len(desc) < 80:
            tail = f"{name}专注{ind}领域多年,提供专业{ind}服务与一站式解决方案" if name and ind else "提供专业服务与一站式解决方案"
            desc = f"{desc}。{tail},是您值得信赖的选择。"
        # meta_description: 确保最终长度>=50字符
        meta = ctx.get('meta_description', '')
        if not meta:
            ctx["meta_description"] = desc
        elif len(meta) < 50:
            # AI meta太短,用补强后的desc替代
            ctx["meta_description"] = desc if len(desc) >= 50 else f"{desc}欢迎访问官网了解更多详情。"
        elif len(meta) < 80 and len(desc) > len(meta):
            # desc更长,用desc
            ctx["meta_description"] = desc
        elif len(meta) < 80:
            # meta不够长但desc也不更好,追加更多信息
            name = ctx.get('name', '')
            ind = ctx.get('industry', '')
            # 优先追加"欢迎访问官网了解更多详情"
            append_text = ",欢迎访问官网了解更多详情。"
            if append_text.lstrip(",") not in meta:
                meta_trimmed = meta.rstrip("。,、!?;:")
                meta = meta_trimmed + append_text
            # 如果追加后仍不够长,再追加行业信息
            if len(meta) < 80 and name and ind:
                extra = f"{name}是{ind}领域值得信赖的合作伙伴。"
                if name not in meta[-20:]:  # 避免紧邻重复
                    meta = meta.rstrip("。,、!?;:") + "。" + extra
            ctx["meta_description"] = meta
        else:
            ctx["meta_description"] = meta
        ctx.setdefault("meta_keywords", ctx.get("industry", ""))
        ctx.setdefault("stats", [])
        ctx.setdefault("website", "")
        # landing
        ctx.setdefault("features", [])
        ctx.setdefault("testimonials", [])
        ctx.setdefault("faq", [])
        ctx.setdefault("hero_headline", f"{ctx.get('name', '')}·{ctx.get('industry', '')}领航者" if ctx.get('name') else "")
        # H1补强:太短时追加行业信息,确保SEO有效
        hh = ctx.get("hero_headline", "")
        if 0 < len(hh) < 15 and ctx.get('industry'):
            ctx["hero_headline"] = f"{hh} · {ctx['industry']}专业服务"
        ctx.setdefault("hero_subheadline", "")
        ctx.setdefault("hero_cta", "了解更多")
        ctx.setdefault("features_title", "特色")
        ctx.setdefault("about_title", "关于我们")
        ctx.setdefault("about_content", "")
        ctx.setdefault("testimonials_title", "客户评价")
        ctx.setdefault("faq_title", "常见问题")
        ctx.setdefault("cta_headline", "联系我们")
        ctx.setdefault("cta_subheadline", "")
        ctx.setdefault("cta_button", "免费咨询")
        # process steps
        ctx.setdefault("process_title", "")
        ctx.setdefault("process_subtitle", "")
        ctx.setdefault("process_steps", [])
        # cta trust badges / guarantee
        ctx.setdefault("cta_trust_badges", [])
        ctx.setdefault("cta_guarantee", "")
        # pricing
        ctx.setdefault("hero_title", ctx.get("hero_headline", "定价方案"))
        ctx.setdefault("hero_subtitle", ctx.get("hero_subheadline", ""))
        ctx.setdefault("pricing_note", "")
        ctx.setdefault("plans", [])
        ctx.setdefault("cta_title", ctx.get("cta_headline", "还有疑问?"))
        ctx.setdefault("cta_subtitle", ctx.get("cta_subheadline", ""))
        # site
        ctx.setdefault("services_title", "服务")
        ctx.setdefault("services", [])
        ctx.setdefault("about_summary", "")
        ctx.setdefault("story_title", "品牌故事")
        ctx.setdefault("story_content", "")
        ctx.setdefault("team_title", "核心团队")
        ctx.setdefault("team", [])
        ctx.setdefault("values_title", "企业价值观")
        ctx.setdefault("values", [])
        ctx.setdefault("products_title", "产品与服务")
        ctx.setdefault("products_subtitle", "")
        ctx.setdefault("products", [])
        ctx.setdefault("blog_title", "博客")
        ctx.setdefault("blog_subtitle", "")
        ctx.setdefault("articles", [])
        ctx.setdefault("contact_headline", ctx.get("cta_headline", "联系我们"))
        ctx.setdefault("contact_subtitle", ctx.get("cta_subheadline", ""))
        # shop
        ctx.setdefault("site_id", "")
        ctx.setdefault("api_base_url", "")
        ctx.setdefault("theme", "tech_blue")
        ctx.setdefault("currency", "CNY")
        ctx.setdefault("currency_symbol", "\u00a5")
        ctx.setdefault("customer_service_url", "")
        ctx.setdefault("ga_id", "")
        ctx.setdefault("baidu_tongji_id", "")
        ctx.setdefault("trust_stats", [])
        ctx.setdefault("brand_story_title", "\u54c1\u724c\u6545\u4e8b")
        ctx.setdefault("brand_story_content", "")
        ctx.setdefault("advantages", [])
        ctx.setdefault("banner_slides", [])
        ctx.setdefault("footer_about", "")
        ctx.setdefault("footer_links", {})
        ctx.setdefault("is_pro", False)
        ctx.setdefault("shop_name", ctx.get("name", ""))
        ctx.setdefault("shop_slogan", ctx.get("hero_subheadline", ""))
        ctx.setdefault("json_ld", "{}")
        # ── 行业主题图片注入 ──
        _INDUSTRY_IMAGES = {
            "物流运输": {"hero": "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?w=1200&q=80", "about": "https://images.unsplash.com/photo-1578575437130-527eed3abbec?w=600&q=80", "features": ["https://images.unsplash.com/photo-1553413077-190dd305871c?w=400&q=80", "https://images.unsplash.com/photo-1601584115197-04ecc0da31d7?w=400&q=80", "https://images.unsplash.com/photo-1519003722824-194d4455a60c?w=400&q=80", "https://images.unsplash.com/photo-1558618666-fcd25c85f82e?w=400&q=80"]},
            "教育培训": {"hero": "https://images.unsplash.com/photo-1523050854058-8df90110c476?w=1200&q=80", "about": "https://images.unsplash.com/photo-1509062522246-3755977927d7?w=600&q=80", "features": ["https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=400&q=80", "https://images.unsplash.com/photo-1509062522246-3755977927d7?w=400&q=80", "https://images.unsplash.com/photo-1427504494785-3a9ca7044f45?w=400&q=80", "https://images.unsplash.com/photo-1571260899304-425eee4c7efc?w=400&q=80"]},
            "医疗健康": {"hero": "https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?w=1200&q=80", "about": "https://images.unsplash.com/photo-1631815588090-d4bfec5b1ccb?w=600&q=80", "features": ["https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=400&q=80", "https://images.unsplash.com/photo-1584820927498-cfe5211fd8bf?w=400&q=80", "https://images.unsplash.com/photo-1576091160550-2173dba999ef?w=400&q=80", "https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?w=400&q=80"]},
            "餐饮美食": {"hero": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=1200&q=80", "about": "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=600&q=80", "features": ["https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=400&q=80", "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=400&q=80", "https://images.unsplash.com/photo-1551218808-94e220e084d2?w=400&q=80", "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=400&q=80"]},
            "科技软件": {"hero": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200&q=80", "about": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=600&q=80", "features": ["https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=400&q=80", "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=400&q=80", "https://images.unsplash.com/photo-1555949963-ff9fe0c870eb?w=400&q=80", "https://images.unsplash.com/photo-1563986768609-322da13575f2?w=400&q=80"]},
            "房产建筑": {"hero": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1200&q=80", "about": "https://images.unsplash.com/photo-1503387762-592deb58ef4e?w=600&q=80", "features": ["https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=400&q=80", "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=400&q=80", "https://images.unsplash.com/photo-1574362848149-11496d93a7c7?w=400&q=80", "https://images.unsplash.com/photo-1560520653-9e0e4c89eb11?w=400&q=80"]},
            "美容美发": {"hero": "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=1200&q=80", "about": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=600&q=80", "features": ["https://images.unsplash.com/photo-1521590832167-7bcbfaa6381f?w=400&q=80", "https://images.unsplash.com/photo-1516975080664-ed2fc6a32937?w=400&q=80", "https://images.unsplash.com/photo-1562322140-8baeececf3df?w=400&q=80", "https://images.unsplash.com/photo-1580618672591-eb180b1a973f?w=400&q=80"]},
            "法律服务": {"hero": "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=1200&q=80", "about": "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=600&q=80", "features": ["https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=400&q=80", "https://images.unsplash.com/photo-1450101499163-c8848c66ca85?w=400&q=80", "https://images.unsplash.com/photo-1521791055366-0d553872125f?w=400&q=80", "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&q=80"]},
            "教育": {"hero": "https://images.unsplash.com/photo-1523050854058-8df90110c476?w=1200&q=80", "about": "https://images.unsplash.com/photo-1509062522246-3755977927d7?w=600&q=80", "features": ["https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=400&q=80", "https://images.unsplash.com/photo-1509062522246-3755977927d7?w=400&q=80", "https://images.unsplash.com/photo-1427504494785-3a9ca7044f45?w=400&q=80", "https://images.unsplash.com/photo-1571260899304-425eee4c7efc?w=400&q=80"]},
            "房地产": {"hero": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1200&q=80", "about": "https://images.unsplash.com/photo-1503387762-592deb58ef4e?w=600&q=80", "features": ["https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=400&q=80", "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=400&q=80", "https://images.unsplash.com/photo-1574362848149-11496d93a7c7?w=400&q=80", "https://images.unsplash.com/photo-1560520653-9e0e4c89eb11?w=400&q=80"]},
            "法律咨询": {"hero": "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=1200&q=80", "about": "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=600&q=80", "features": ["https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=400&q=80", "https://images.unsplash.com/photo-1450101499163-c8848c66ca85?w=400&q=80", "https://images.unsplash.com/photo-1521791055366-0d553872125f?w=400&q=80", "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&q=80"]},
            "金融保险": {"hero": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1200&q=80", "about": "https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=600&q=80", "features": ["https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=400&q=80", "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=400&q=80", "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=400&q=80", "https://images.unsplash.com/photo-1563986768609-322da13575f2?w=400&q=80"]},
            "装修建材": {"hero": "https://images.unsplash.com/photo-1503387762-592deb58ef4e?w=1200&q=80", "about": "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=600&q=80", "features": ["https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=400&q=80", "https://images.unsplash.com/photo-1503387762-592deb58ef4e?w=400&q=80", "https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=400&q=80", "https://images.unsplash.com/photo-1574362848149-11496d93a7c7?w=400&q=80"]},
            "汽车服务": {"hero": "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=1200&q=80", "about": "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=600&q=80", "features": ["https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=400&q=80", "https://images.unsplash.com/photo-1549317661-bd32c8ce0afe?w=400&q=80", "https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=400&q=80", "https://images.unsplash.com/photo-1542362567-b07e54358753?w=400&q=80"]},
            "旅游酒店": {"hero": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1200&q=80", "about": "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=600&q=80", "features": ["https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=400&q=80", "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=400&q=80", "https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=400&q=80", "https://images.unsplash.com/photo-1504280390367-361c6d9f38f4?w=400&q=80"]},
            "健身运动": {"hero": "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=1200&q=80", "about": "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=600&q=80", "features": ["https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=400&q=80", "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=400&q=80", "https://images.unsplash.com/photo-1540497077202-7c8a3999166f?w=400&q=80", "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=400&q=80"]},
            "default": {"hero": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1200&q=80", "about": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=600&q=80", "features": ["https://images.unsplash.com/photo-1497366216548-37526070297c?w=400&q=80"] * 4},
        }
        img_data = _INDUSTRY_IMAGES.get(ctx.get("industry", ""), _INDUSTRY_IMAGES.get("default", {}))
        if not ctx.get("hero_image"): ctx["hero_image"] = img_data.get("hero", "")
        if not ctx.get("about_image"): ctx["about_image"] = img_data.get("about", "")
        feature_imgs = img_data.get("features", [])
        for i, feat in enumerate(ctx.get("features", [])):
            if i < len(feature_imgs) and not feat.get("image"):
                feat["image"] = feature_imgs[i]
        if not ctx.get("og_image"): ctx["og_image"] = img_data.get("hero", "")
        # ── 行业SVG插画注入 ──
        _INDUSTRY_SVG = {
            "物流运输": '<div class="hero-illustration"><svg viewBox="0 0 320 260" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="60" y="120" width="200" height="80" rx="8" fill="white" opacity=".12"/><rect x="80" y="90" width="100" height="70" rx="6" fill="white" opacity=".18"/><rect x="180" y="100" width="80" height="60" rx="4" fill="white" opacity=".08"/><circle cx="110" cy="205" r="15" stroke="white" stroke-width="2" opacity=".2"/><circle cx="210" cy="205" r="15" stroke="white" stroke-width="2" opacity=".2"/><path d="M140 130l20-20 20 20" stroke="white" stroke-width="2" stroke-linecap="round" opacity=".25"/></svg></div>',
            "科技": '<div class="hero-illustration"><svg viewBox="0 0 320 260" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="40" y="60" width="240" height="140" rx="12" fill="white" opacity=".1"/><rect x="60" y="80" width="80" height="8" rx="4" fill="white" opacity=".25"/><rect x="60" y="96" width="60" height="6" rx="3" fill="white" opacity=".15"/><rect x="60" y="110" width="120" height="6" rx="3" fill="white" opacity=".1"/><circle cx="230" cy="100" r="30" stroke="white" stroke-width="1.5" opacity=".15"/><path d="M218 100l8 8 16-16" stroke="white" stroke-width="2" stroke-linecap="round" opacity=".25"/><rect x="60" y="140" width="200" height="30" rx="6" fill="white" opacity=".06"/><rect x="75" y="150" width="40" height="10" rx="3" fill="white" opacity=".12"/></svg></div>',
            "医疗健康": '<div class="hero-illustration"><svg viewBox="0 0 320 260" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="60" y="60" width="200" height="140" rx="16" fill="white" opacity=".08"/><path d="M160 90v60M130 120h60" stroke="white" stroke-width="6" stroke-linecap="round" opacity=".2"/><circle cx="160" cy="120" r="40" stroke="white" stroke-width="1.5" opacity=".12"/><rect x="80" y="170" width="50" height="8" rx="4" fill="white" opacity=".1"/><rect x="190" y="170" width="50" height="8" rx="4" fill="white" opacity=".1"/></svg></div>',
            "餐饮美食": '<div class="hero-illustration"><svg viewBox="0 0 320 260" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="160" cy="110" r="50" stroke="white" stroke-width="2" opacity=".15"/><path d="M160 75v20M140 95h40" stroke="white" stroke-width="2" stroke-linecap="round" opacity=".2"/><rect x="100" y="150" width="120" height="40" rx="8" fill="white" opacity=".08"/><rect x="120" y="162" width="80" height="6" rx="3" fill="white" opacity=".12"/><circle cx="110" cy="110" r="8" fill="white" opacity=".06"/><circle cx="210" cy="110" r="8" fill="white" opacity=".06"/></svg></div>',
            "default": '<div class="hero-illustration"><svg viewBox="0 0 320 260" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="40" y="60" width="240" height="140" rx="12" fill="white" opacity=".1"/><rect x="60" y="85" width="80" height="8" rx="4" fill="white" opacity=".2"/><rect x="60" y="101" width="120" height="6" rx="3" fill="white" opacity=".12"/><circle cx="230" cy="100" r="30" stroke="white" stroke-width="1.5" opacity=".15"/><path d="M218 100l8 8 16-16" stroke="white" stroke-width="2" stroke-linecap="round" opacity=".2"/><rect x="60" y="130" width="200" height="30" rx="6" fill="white" opacity=".06"/></svg></div>',
        }
        if not ctx.get("hero_illustration"):
            ind = ctx.get("industry", "")
            ctx["hero_illustration"] = _INDUSTRY_SVG.get(ind, _INDUSTRY_SVG.get("default", ""))
        return ctx
