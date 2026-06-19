"""
builders.site_planner — 站点规划器（业务逻辑层）

对 Engine 的高级封装：
1. 接收用户自然语言输入（"我要一个卖手工皂的网站"）
2. 自动提取关键信息（品牌名、行业、功能需求等）
3. 规划站点结构（几页、什么布局）
4. 协调 Engine 完成生成

这是 Engine 和 API 之间的"业务层"。
"""

from __future__ import annotations

import re
import logging
from typing import Any

from core.engine import SiteBuilderEngine, get_engine

logger = logging.getLogger("site-builder.planner")


class SitePlanner:
    """
    站点规划器。

    接收用户的自然语言需求，自动：
    - 提取关键信息
    - 选择生成模式（着陆页 / 完整网站 / 定价页）
    - 并发生成多页
    """

    # 需求关键词 → 生成模式映射
    _MODE_KEYWORDS = {
        "landing": ["着陆页", "落地页", "单页", "landing", "宣传页"],
        "site": ["网站", "官网", "完整", "多页", "全部", "site"],
        "pricing": ["定价", "价格", "方案", "套餐", "pricing", "收费"],
    }

    def __init__(self, engine: SiteBuilderEngine | None = None):
        self._engine = engine

    async def _get_engine(self) -> SiteBuilderEngine:
        if self._engine is None:
            self._engine = await get_engine()
        return self._engine

    async def process(self, user_input: str, **extra) -> dict[str, Any]:
        """
        处理用户需求，生成站点。

        Args:
            user_input: 自然语言需求描述
            **extra: phone, email, address, website 等补充信息

        Returns:
            Engine 的构建结果
        """
        # 1. 提取信息
        info = self._parse_input(user_input)
        info.update({k: v for k, v in extra.items() if v})

        # 2. 推断模式
        mode = self._infer_mode(user_input)

        # 3. 生成
        engine = await self._get_engine()
        logger.info(f"规划完成: mode={mode}, info={info}")

        match mode:
            case "landing":
                return await engine.build_landing(info)
            case "site":
                return await engine.build_site(info)
            case "pricing":
                return await engine.build_pricing(info)
            case _:
                return await engine.build_landing(info)

    def _parse_input(self, text: str) -> dict[str, str]:
        """从自然语言中提取结构化信息"""
        info = {
            "name": "",
            "industry": "",
            "description": text.strip(),
            "keywords": "",
            "audience": "",
        }

        # 尝试提取品牌名: "叫XX的网站", "一个XX的网站", "我的品牌是XX"
        name_patterns = [
            r'(?:叫|叫做|是|品牌[是叫]*)\s*["「『]?([^"「『」』\s，,]+)["」』]?\s*(?:的|网站|品牌|公司|店)',
            r'我(?:要|想|需要)(?:一个|做)\s*["「『]?([^"「『」』\s，,]+)["」』]?\s*(?:的|网站|品牌)',
            r'(?:卖|做|经营)\s*(.+?)\s*(?:的|网站|品牌|公司|店)',
        ]
        for pattern in name_patterns:
            m = re.search(pattern, text)
            if m:
                info["name"] = m.group(1).strip()
                break

        # 尝试提取行业: "卖XX的" → 行业
        industry_patterns = [
            r"卖\s*(.+?)\s*的",
            r"做\s*(.+?)\s*(?:的|行业|生意)",
            r"(?:从事|涉足)\s*(.+?)\s*(?:行业|领域)",
        ]
        for pattern in industry_patterns:
            m = re.search(pattern, text)
            if m:
                info["industry"] = m.group(1).strip()
                break

        if not info["name"]:
            # 取文本前几个字作为名称
            words = text.replace("，", ",").replace("。", ",").split(",")
            if words:
                first = words[0].strip()
                if len(first) > 2:
                    info["name"] = first[:12]
                else:
                    info["name"] = text.strip()[:15]

        return info

    def _infer_mode(self, text: str) -> str:
        """根据关键词推断生成模式"""
        scores = {"landing": 0, "site": 0, "pricing": 0}
        text_lower = text.lower()
        for mode, keywords in self._MODE_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    scores[mode] += 1

        # 默认着陆页
        max_score = max(scores.values())
        if max_score == 0:
            return "landing"

        # 返回得分最高的模式
        for mode, score in scores.items():
            if score == max_score:
                return mode
        return "landing"