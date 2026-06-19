"""
core.backends.ai.glm — 智谱 GLM API 后端

通过智谱 AI 开放平台 (https://open.bigmodel.cn) 调用 GLM-4 生成站点内容。
"""

from __future__ import annotations

import json as _json
import logging
import re
from typing import Any

from core.backends.base import AIBackend

logger = logging.getLogger("site-builder.ai.glm")

try:
    import httpx

    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False


class GLMBackend(AIBackend):
    """
    智谱 GLM-4 后端。

    优先级 20，仅次于 DeepSeek。
    """

    name = "glm"
    priority = 20
    display_name = "GLM-4"

    API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    DEFAULT_MODEL = "glm-4-flash"

    def __init__(self, api_key: str = "", model: str = "", base_url: str = ""):
        import os

        self.api_key = api_key or os.environ.get("ZHIPUAI_API_KEY", "")
        self.model = model or self.DEFAULT_MODEL
        self.base_url = base_url or self.API_URL

    @classmethod
    def _check_dependencies(cls) -> None:
        if not _HTTPX_AVAILABLE:
            raise ImportError("httpx 未安装: pip install httpx")

    async def health_check(self) -> bool:
        if not self.api_key:
            return False
        try:
            import httpx

            async with httpx.AsyncClient(timeout=httpx.Timeout(5)) as client:
                r = await client.get(
                    "https://open.bigmodel.cn/api/paas/v4/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                return r.status_code == 200
        except Exception:
            return False

    async def generate(self, prompt: str, **kwargs) -> dict[str, Any]:
        import httpx

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是专业的SEO和网站内容生成助手。必须只返回有效的JSON，不要加任何额外说明。",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }

        self._last_api_error = None
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30, read=90),
        ) as client:
            r = await client.post(self.base_url, json=payload, headers=headers)
            if r.status_code != 200:
                self._last_api_error = f"GLM {r.status_code}: {r.text[:300]}"
                logger.error(self._last_api_error)
                r.raise_for_status()
            data = r.json()

        content = data["choices"][0]["message"]["content"]
        return self._parse_json(content)

    @property
    def last_api_error(self):
        return getattr(self, '_last_api_error', None)

    def _parse_json(self, raw: str) -> dict:
        raw = raw.strip()
        try:
            return _json.loads(raw)
        except _json.JSONDecodeError:
            pass
        for pattern in [r"```json\s*\n(.*?)\n```", r"```\s*\n(.*?)\n```", r"```(.*?)```"]:
            m = re.search(pattern, raw, re.DOTALL)
            if m:
                try:
                    return _json.loads(m.group(1).strip())
                except _json.JSONDecodeError:
                    continue
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                return _json.loads(m.group(0))
            except _json.JSONDecodeError:
                pass
        raise ValueError(f"GLM 返回无法解析为 JSON: {raw[:200]}...")
