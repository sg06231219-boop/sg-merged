"""
core.seo_engine — 程序化SEO引擎

核心差异化功能：输入行业+种子词 → 自动挖掘长尾关键词 → 批量生成SEO优化页面 → 内链网络 → Sitemap

这不再是"又一个AI建站工具"，而是完整的程序化SEO内容工厂。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger("site-builder.seo")

# ═══════════════════════════════════════════════════════════
#  关键词意图分类
# ═══════════════════════════════════════════════════════════

class KeywordIntent(Enum):
    INFORMATIONAL = "informational"   # 了解/科普类
    TRANSACTIONAL = "transactional"   # 购买/服务类
    NAVIGATIONAL  = "navigational"    # 品牌/地点类
    COMPARISON    = "comparison"      # 对比/评测类


@dataclass
class Keyword:
    text: str
    intent: KeywordIntent
    search_volume: int = 0       # 预估搜索量（模拟）
    difficulty: float = 0.0      # 竞争难度 0-1
    cluster_id: str = ""
    parent_keyword: str = ""


@dataclass
class SEOTask:
    task_id: str
    industry: str
    seed_keywords: list[str]
    city: str = ""
    status: str = "pending"      # pending → generating → linking → done / error
    keywords: list[Keyword] = field(default_factory=list)
    pages: list[dict] = field(default_factory=list)
    sitemap_path: str = ""
    created_at: str = ""
    finished_at: str = ""
    error: str = ""
    progress: int = 0            # 0-100
    total_keywords: int = 0
    total_pages: int = 0


# ═══════════════════════════════════════════════════════════
#  行业关键词模板库
# ═══════════════════════════════════════════════════════════

# 每个行业：种子模板 × 城市 × 修饰词 = 长尾关键词矩阵

_INDUSTRY_TEMPLATES: dict[str, dict] = {
    "科技": {
        "seeds": ["软件开发", "APP开发", "小程序", "SaaS系统", "企业系统", "云计算", "AI应用", "数据分析"],
        "modifiers": {
            KeywordIntent.TRANSACTIONAL: ["公司", "服务商", "外包", "定制", "开发公司", "哪家好"],
            KeywordIntent.INFORMATIONAL: ["多少钱", "费用", "流程", "方案", "怎么选", "区别", "优缺点"],
            KeywordIntent.COMPARISON:    ["对比", "评测", "排名", "排行", "推荐", "哪家强"],
            KeywordIntent.NAVIGATIONAL:  ["附近", "本地", "上门"],
        },
        "features": ["API接口", "数据加密", "云端部署", "实时同步", "多端适配"],
    },
    "教育": {
        "seeds": ["雅思培训", "托福培训", "考研辅导", "公考培训", "职业培训", "少儿编程", "英语口语", "留学咨询"],
        "modifiers": {
            KeywordIntent.TRANSACTIONAL: ["机构", "培训班", "课程", "学校", "中心", "报名"],
            KeywordIntent.INFORMATIONAL: ["多少钱", "费用", "通过率", "多久", "怎么准备", "攻略"],
            KeywordIntent.COMPARISON:    ["对比", "评测", "排名", "哪家好", "推荐"],
            KeywordIntent.NAVIGATIONAL:  ["附近", "本地", "线下"],
        },
        "features": ["名师授课", "1对1辅导", "在线直播", "题库系统", "保分协议"],
    },
    "医疗": {
        "seeds": ["口腔医院", "体检中心", "中医馆", "医美", "眼科", "骨科", "儿科", "心理咨询"],
        "modifiers": {
            KeywordIntent.TRANSACTIONAL: ["医院", "诊所", "门诊", "预约", "挂号", "哪家好"],
            KeywordIntent.INFORMATIONAL: ["多少钱", "费用", "医保", "流程", "注意事项", "恢复期"],
            KeywordIntent.COMPARISON:    ["排名", "排行", "推荐", "对比", "评价"],
            KeywordIntent.NAVIGATIONAL:  ["附近", "本地", "地址"],
        },
        "features": ["专家坐诊", "在线问诊", "电子处方", "预约提醒", "健康档案"],
    },
    "法律": {
        "seeds": ["离婚律师", "刑事律师", "合同纠纷", "劳动仲裁", "知识产权", "公司注册", "房产纠纷", "交通事故"],
        "modifiers": {
            KeywordIntent.TRANSACTIONAL: ["律师", "律所", "事务所", "咨询", "代理", "代办"],
            KeywordIntent.INFORMATIONAL: ["多少钱", "费用", "流程", "条件", "怎么办", "需要什么"],
            KeywordIntent.COMPARISON:    ["排名", "推荐", "评价", "哪家好"],
            KeywordIntent.NAVIGATIONAL:  ["附近", "本地"],
        },
        "features": ["在线咨询", "案件评估", "风险分析", "文书代写", "全程代理"],
    },
    "装修": {
        "seeds": ["家装设计", "办公室装修", "店铺装修", "别墅装修", "旧房翻新", "全屋定制", "软装设计", "智能家居"],
        "modifiers": {
            KeywordIntent.TRANSACTIONAL: ["公司", "设计", "施工", "报价", "套餐", "哪家好"],
            KeywordIntent.INFORMATIONAL: ["多少钱", "费用", "预算", "流程", "工期", "注意事项", "避坑"],
            KeywordIntent.COMPARISON:    ["对比", "排名", "推荐", "排行", "评价"],
            KeywordIntent.NAVIGATIONAL:  ["附近", "本地"],
        },
        "features": ["免费量房", "3D效果图", "环保材料", "0增项", "质保5年"],
    },
    "餐饮": {
        "seeds": ["火锅", "烧烤", "日料", "西餐", "奶茶", "烘焙", "快餐", "私房菜"],
        "modifiers": {
            KeywordIntent.TRANSACTIONAL: ["加盟", "开店", "培训", "配方", "设备"],
            KeywordIntent.INFORMATIONAL: ["多少钱", "投资", "利润", "前景", "流程", "怎么做"],
            KeywordIntent.COMPARISON:    ["排名", "推荐", "品牌对比", "评测"],
            KeywordIntent.NAVIGATIONAL:  ["附近", "本地", "地址"],
        },
        "features": ["外卖配送", "在线预约", "会员系统", "排队叫号", "营养分析"],
    },
    "物流": {
        "seeds": ["货运", "快递", "冷链", "仓储", "跨境物流", "搬家", "大件运输", "供应链"],
        "modifiers": {
            KeywordIntent.TRANSACTIONAL: ["公司", "服务", "外包", "代理", "报价", "哪家好"],
            KeywordIntent.INFORMATIONAL: ["多少钱", "费用", "时效", "流程", "怎么寄", "注意事项"],
            KeywordIntent.COMPARISON:    ["对比", "排名", "推荐", "评价"],
            KeywordIntent.NAVIGATIONAL:  ["附近", "本地"],
        },
        "features": ["实时追踪", "上门取件", "保价服务", "电子面单", "智能分拣"],
    },
    "金融": {
        "seeds": ["贷款", "理财", "保险", "信用卡", "股票", "基金", "税务", "审计"],
        "modifiers": {
            KeywordIntent.TRANSACTIONAL: ["公司", "平台", "产品", "办理", "申请", "开户"],
            KeywordIntent.INFORMATIONAL: ["利率", "手续费", "条件", "流程", "风险", "怎么选"],
            KeywordIntent.COMPARISON:    ["对比", "排名", "推荐", "评测"],
            KeywordIntent.NAVIGATIONAL:  ["附近", "本地", "网点"],
        },
        "features": ["在线申请", "智能风控", "实时到账", "合规保障", "数据加密"],
    },
}

# 通用行业（未在模板库中的行业使用）
_DEFAULT_TEMPLATE = {
    "seeds": ["服务", "解决方案", "咨询", "培训", "设计", "代理"],
    "modifiers": {
        KeywordIntent.TRANSACTIONAL: ["公司", "服务商", "机构", "平台", "哪家好"],
        KeywordIntent.INFORMATIONAL: ["多少钱", "费用", "流程", "方案", "怎么选"],
        KeywordIntent.COMPARISON:    ["对比", "排名", "推荐", "评价"],
        KeywordIntent.NAVIGATIONAL:  ["附近", "本地"],
    },
    "features": ["专业团队", "在线服务", "免费咨询", "定制方案", "售后保障"],
}

# 城市列表（用于地域词扩展）
_TIER1_CITIES = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "南京", "重庆", "西安"]


# ═══════════════════════════════════════════════════════════
#  关键词挖掘器
# ═══════════════════════════════════════════════════════════

class KeywordExpander:
    """从种子词+行业扩展出长尾关键词矩阵"""

    def expand(self, industry: str, seed_keywords: list[str], city: str = "",
               max_keywords: int = 200) -> list[Keyword]:
        """
        核心算法：种子词 × 修饰词 × 城市 = 长尾关键词矩阵
        
        示例：
          种子="软件开发" × 修饰="公司" × 城市="杭州" → "杭州软件开发公司"
          种子="雅思培训" × 修饰="多少钱" × 城市=""   → "雅思培训多少钱"
        """
        tpl = self._get_template(industry)
        keywords: list[Keyword] = []

        # 1. 种子词 × 修饰词（核心矩阵）
        for seed in seed_keywords:
            for intent, mods in tpl["modifiers"].items():
                for mod in mods:
                    kw_text = f"{city}{seed}{mod}" if city else f"{seed}{mod}"
                    kw = Keyword(
                        text=kw_text,
                        intent=intent,
                        search_volume=self._estimate_volume(kw_text, intent),
                        difficulty=self._estimate_difficulty(kw_text, intent),
                        parent_keyword=seed,
                    )
                    keywords.append(kw)

        # 2. 行业模板种子词 × 修饰词（补充覆盖）
        tpl_seeds = [s for s in tpl["seeds"] if s not in seed_keywords]
        for seed in tpl_seeds[:4]:  # 取前4个补充
            for intent, mods in tpl["modifiers"].items():
                for mod in mods[:2]:  # 每意图取2个修饰
                    kw_text = f"{city}{seed}{mod}" if city else f"{seed}{mod}"
                    kw = Keyword(
                        text=kw_text,
                        intent=intent,
                        search_volume=self._estimate_volume(kw_text, intent),
                        difficulty=self._estimate_difficulty(kw_text, intent),
                        parent_keyword=seed,
                    )
                    keywords.append(kw)

        # 3. 城市变体（如果指定了城市，补充其他城市变体）
        if city:
            other_cities = [c for c in _TIER1_CITIES if c != city][:3]
            for c in other_cities:
                for seed in seed_keywords[:3]:
                    for mod in list(tpl["modifiers"].get(KeywordIntent.TRANSACTIONAL, []))[:2]:
                        kw_text = f"{c}{seed}{mod}"
                        kw = Keyword(
                            text=kw_text,
                            intent=KeywordIntent.TRANSACTIONAL,
                            search_volume=self._estimate_volume(kw_text, KeywordIntent.TRANSACTIONAL),
                            difficulty=self._estimate_difficulty(kw_text, KeywordIntent.TRANSACTIONAL),
                            parent_keyword=seed,
                        )
                        keywords.append(kw)

        # 4. 去重 + 截断
        seen = set()
        unique = []
        for kw in keywords:
            if kw.text not in seen:
                seen.add(kw.text)
                unique.append(kw)
        
        # 按搜索量排序，截断
        unique.sort(key=lambda k: k.search_volume, reverse=True)
        return unique[:max_keywords]

    def _get_template(self, industry: str) -> dict:
        """获取行业模板，未匹配则用默认"""
        for key, tpl in _INDUSTRY_TEMPLATES.items():
            if key in industry or industry in key:
                return tpl
        return _DEFAULT_TEMPLATE

    def _estimate_volume(self, kw: str, intent: KeywordIntent) -> int:
        """模拟搜索量（实际项目可接Google Keyword Planner API）"""
        base = {
            KeywordIntent.TRANSACTIONAL: 800,
            KeywordIntent.INFORMATIONAL: 1200,
            KeywordIntent.COMPARISON:    600,
            KeywordIntent.NAVIGATIONAL:  400,
        }
        # 长尾词越长，搜索量越低
        length_penalty = max(0.3, 1.0 - len(kw) * 0.02)
        import random
        return int(base.get(intent, 500) * length_penalty * random.uniform(0.6, 1.4))

    def _estimate_difficulty(self, kw: str, intent: KeywordIntent) -> float:
        """模拟竞争难度"""
        base = {
            KeywordIntent.TRANSACTIONAL: 0.7,
            KeywordIntent.INFORMATIONAL: 0.4,
            KeywordIntent.COMPARISON:    0.6,
            KeywordIntent.NAVIGATIONAL:  0.3,
        }
        # 长尾词越长，竞争越低
        length_bonus = min(0.3, len(kw) * 0.01)
        return max(0.1, min(0.95, base.get(intent, 0.5) - length_bonus))


# ═══════════════════════════════════════════════════════════
#  关键词聚类器
# ═══════════════════════════════════════════════════════════

class KeywordClusterer:
    """按意图和语义聚类关键词"""

    def cluster(self, keywords: list[Keyword]) -> list[Keyword]:
        """为每个关键词分配cluster_id"""
        clusters: dict[str, list[Keyword]] = {}

        for kw in keywords:
            # 简单聚类策略：parent_keyword + intent = 同一簇
            cluster_key = f"{kw.parent_keyword}_{kw.intent.value}"
            if cluster_key not in clusters:
                clusters[cluster_key] = []
            clusters[cluster_key].append(kw)

        # 分配cluster_id
        for i, (key, members) in enumerate(clusters.items()):
            cid = f"cluster_{i:03d}"
            for kw in members:
                kw.cluster_id = cid

        return keywords


# ═══════════════════════════════════════════════════════════
#  内链网络构建器
# ═══════════════════════════════════════════════════════════

class InternalLinker:
    """构建页面间的内链网络，提升SEO权重传递"""

    def build_links(self, pages: list[dict], keywords: list[Keyword]) -> list[dict]:
        """
        为每个页面注入内链：
        1. 同簇页面互链（2-3个）
        2. 交易型页面链接到信息型页面（知识图谱）
        3. 面包屑导航
        """
        # 按簇分组
        cluster_map: dict[str, list[int]] = {}
        for i, kw in enumerate(keywords):
            if i >= len(pages):
                break
            cid = kw.cluster_id
            if cid not in cluster_map:
                cluster_map[cid] = []
            cluster_map[cid].append(i)

        for i, page in enumerate(pages):
            kw = keywords[i] if i < len(keywords) else None
            if not kw:
                continue

            related_links = []

            # 同簇互链（最多3个）
            same_cluster = cluster_map.get(kw.cluster_id, [])
            for j in same_cluster:
                if j != i and len(related_links) < 3:
                    related_links.append({
                        "title": pages[j].get("keyword", ""),
                        "url": pages[j].get("filename", ""),
                        "relation": "same_cluster",
                    })

            # 交易型→信息型互链
            if kw.intent == KeywordIntent.TRANSACTIONAL:
                for j, okw in enumerate(keywords):
                    if j < len(pages) and okw.intent == KeywordIntent.INFORMATIONAL \
                       and okw.parent_keyword == kw.parent_keyword \
                       and len(related_links) < 5:
                        related_links.append({
                            "title": pages[j].get("keyword", ""),
                            "url": pages[j].get("filename", ""),
                            "relation": "knowledge_graph",
                        })

            page["related_links"] = related_links
            page["breadcrumb"] = f"首页 > {kw.parent_keyword} > {kw.text}"

        return pages


# ═══════════════════════════════════════════════════════════
#  Sitemap生成器
# ═══════════════════════════════════════════════════════════

class SitemapGenerator:
    """生成符合标准的sitemap.xml"""

    def generate(self, pages: list[dict], base_url: str = "https://example.com") -> str:
        urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

        for page in pages:
            url_el = ET.SubElement(urlset, "url")
            loc = ET.SubElement(url_el, "loc")
            loc.text = f"{base_url}/{page.get('filename', '')}"
            lastmod = ET.SubElement(url_el, "lastmod")
            lastmod.text = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            changefreq = ET.SubElement(url_el, "changefreq")
            changefreq.text = "weekly"
            priority = ET.SubElement(url_el, "priority")

            # 交易型页面优先级更高
            kw = page.get("keyword_data", {})
            intent = kw.get("intent", "")
            priority.text = "0.8" if intent == "transactional" else "0.6"

        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(urlset, encoding="unicode")


# ═══════════════════════════════════════════════════════════
#  SEO引擎主类
# ═══════════════════════════════════════════════════════════

class SEOEngine:
    """
    程序化SEO引擎 — 一键生成行业关键词矩阵+批量SEO页面+内链网络+Sitemap
    
    工作流：
    1. 用户输入：行业 + 种子词 + 城市
    2. 关键词扩展：种子词 × 修饰词 × 城市 → 长尾关键词矩阵
    3. 关键词聚类：按意图+语义分组
    4. 批量页面生成：每个关键词生成一个SEO优化落地页
    5. 内链网络：页面间自动交叉链接
    6. Sitemap生成：标准sitemap.xml
    """

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir or Path("outputs/seo")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._expander = KeywordExpander()
        self._clusterer = KeywordClusterer()
        self._linker = InternalLinker()
        self._sitemap = SitemapGenerator()
        self._tasks: dict[str, SEOTask] = {}

    def create_task(self, industry: str, seed_keywords: list[str],
                    city: str = "", max_keywords: int = 50) -> SEOTask:
        """创建SEO生成任务"""
        task_id = uuid.uuid4().hex[:12]
        task = SEOTask(
            task_id=task_id,
            industry=industry,
            seed_keywords=seed_keywords,
            city=city,
            created_at=datetime.now(timezone.utc).isoformat(),
            total_keywords=0,
            total_pages=0,
        )
        self._tasks[task_id] = task
        return task

    def expand_keywords(self, task: SEOTask, max_keywords: int = 50) -> list[Keyword]:
        """第一步：关键词挖掘与聚类"""
        # 扩展
        keywords = self._expander.expand(
            task.industry, task.seed_keywords, task.city, max_keywords
        )
        # 聚类
        keywords = self._clusterer.cluster(keywords)

        task.keywords = keywords
        task.total_keywords = len(keywords)
        return keywords

    async def generate_pages(self, task: SEOTask, engine=None,
                             max_pages: int = 50) -> list[dict]:
        """
        第二步：批量生成SEO页面
        engine: SiteBuilderEngine实例，用于调用build_landing
        """
        task.status = "generating"
        keywords = task.keywords[:max_pages]
        pages = []
        total = len(keywords)

        # 并发生成（每批5个，避免API限流）
        batch_size = 5
        for i in range(0, total, batch_size):
            batch = keywords[i:i + batch_size]
            coros = []
            for kw in batch:
                info = {
                    "name": f"{kw.text} — 专业服务",
                    "industry": task.industry,
                    "description": f"关于{kw.text}的专业服务与解决方案，{task.city}地区优质服务商推荐。",
                    "keywords": kw.text,
                    "city": task.city,
                }
                if engine:
                    coros.append(engine.build_landing(info))
                else:
                    coros.append(self._mock_seo_page(kw, task))

            results = await asyncio.gather(*coros, return_exceptions=True)

            for j, result in enumerate(results):
                kw = batch[j]
                if isinstance(result, Exception):
                    logger.error(f"生成失败 [{kw.text}]: {result}")
                    continue

                # 从engine结果提取信息
                if isinstance(result, dict) and "html" in result:
                    page_data = {
                        "keyword": kw.text,
                        "intent": kw.intent.value,
                        "filename": f"{hashlib.md5(kw.text.encode()).hexdigest()[:8]}.html",
                        "page_id": result.get("page_id", ""),
                        "file_size": result.get("file_size", 0),
                        "search_volume": kw.search_volume,
                        "difficulty": kw.difficulty,
                        "cluster_id": kw.cluster_id,
                        "keyword_data": {
                            "text": kw.text,
                            "intent": kw.intent.value,
                            "parent": kw.parent_keyword,
                        },
                    }
                else:
                    page_data = result  # mock返回格式

                pages.append(page_data)

            task.progress = min(100, int((i + batch_size) / total * 100))
            task.total_pages = len(pages)

        task.pages = pages
        return pages

    def build_internal_links(self, task: SEOTask) -> list[dict]:
        """第三步：构建内链网络"""
        task.status = "linking"
        task.pages = self._linker.build_links(task.pages, task.keywords)
        return task.pages

    def generate_sitemap(self, task: SEOTask, base_url: str = "") -> str:
        """第四步：生成Sitemap"""
        sitemap = self._sitemap.generate(task.pages, base_url)
        sitemap_path = self.output_dir / f"sitemap_{task.task_id}.xml"
        sitemap_path.write_text(sitemap, encoding="utf-8")
        task.sitemap_path = str(sitemap_path)
        return sitemap

    async def run_full_pipeline(self, task: SEOTask, engine=None,
                                max_keywords: int = 50, max_pages: int = 50,
                                base_url: str = "") -> SEOTask:
        """一键执行完整SEO流水线"""
        try:
            # Step 1: 关键词挖掘
            self.expand_keywords(task, max_keywords)

            # Step 2: 批量生成页面
            await self.generate_pages(task, engine, max_pages)

            # Step 3: 内链网络
            self.build_internal_links(task)

            # Step 4: Sitemap
            self.generate_sitemap(task, base_url)

            # 保存任务数据
            self._save_task(task)

            task.status = "done"
            task.finished_at = datetime.now(timezone.utc).isoformat()
            task.progress = 100

        except Exception as e:
            task.status = "error"
            task.error = str(e)
            logger.error(f"SEO任务失败 [{task.task_id}]: {e}")

        return task

    def get_task(self, task_id: str) -> SEOTask | None:
        return self._tasks.get(task_id)

    def list_tasks(self) -> list[dict]:
        return [
            {
                "task_id": t.task_id,
                "industry": t.industry,
                "seed_keywords": t.seed_keywords,
                "city": t.city,
                "status": t.status,
                "progress": t.progress,
                "total_keywords": t.total_keywords,
                "total_pages": t.total_pages,
                "created_at": t.created_at,
            }
            for t in self._tasks.values()
        ]

    # ── 辅助方法 ──

    async def _mock_seo_page(self, kw: Keyword, task: SEOTask) -> dict:
        """无engine时的mock页面生成"""
        return {
            "keyword": kw.text,
            "intent": kw.intent.value,
            "filename": f"{hashlib.md5(kw.text.encode()).hexdigest()[:8]}.html",
            "page_id": uuid.uuid4().hex[:8],
            "file_size": 35000 + hash(kw.text) % 20000,
            "search_volume": kw.search_volume,
            "difficulty": kw.difficulty,
            "cluster_id": kw.cluster_id,
            "keyword_data": {
                "text": kw.text,
                "intent": kw.intent.value,
                "parent": kw.parent_keyword,
            },
        }

    def _save_task(self, task: SEOTask):
        """持久化任务数据"""
        task_file = self.output_dir / f"task_{task.task_id}.json"
        data = {
            "task_id": task.task_id,
            "industry": task.industry,
            "seed_keywords": task.seed_keywords,
            "city": task.city,
            "status": task.status,
            "progress": task.progress,
            "total_keywords": task.total_keywords,
            "total_pages": task.total_pages,
            "created_at": task.created_at,
            "finished_at": task.finished_at,
            "keywords": [
                {
                    "text": kw.text,
                    "intent": kw.intent.value,
                    "volume": kw.search_volume,
                    "difficulty": kw.difficulty,
                    "cluster_id": kw.cluster_id,
                    "parent": kw.parent_keyword,
                }
                for kw in task.keywords
            ],
            "pages": task.pages,
            "sitemap_path": task.sitemap_path,
        }
        task_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ═══════════════════════════════════════════════════════════
#  全局单例
# ═══════════════════════════════════════════════════════════

_seo_engine: SEOEngine | None = None


def get_seo_engine() -> SEOEngine:
    global _seo_engine
    if _seo_engine is None:
        _seo_engine = SEOEngine()
    return _seo_engine
