"""
core.backends.ai.deepseek — DeepSeek API 后端

通过 DeepSeek Chat API (https://api.deepseek.com/v1) 生成站点内容。
支持 JSON Mode 输出，自动解析结构化内容。
"""

from __future__ import annotations

import json as _json
import logging
import re
from typing import Any

from core.backends.base import AIBackend

logger = logging.getLogger("site-builder.ai.deepseek")

# 检测 httpx 是否可用
try:
    import httpx

    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False


class DeepSeekBackend(AIBackend):
    """
    DeepSeek API 后端。

    优先级设为 10（最高），最先尝试。
    使用 DeepSeek Chat API，支持 JSON 输出模式。
    """

    name = "deepseek"
    priority = 10
    display_name = "DeepSeek V3"

    # API 配置（可通过环境变量或 init 覆盖）
    API_URL = "https://api.deepseek.com/v1/chat/completions"
    DEFAULT_MODEL = "deepseek-chat"

    def __init__(self, api_key: str = "", model: str = "", base_url: str = ""):
        """
        api_key: DeepSeek API Key（为空则从环境变量 DEEPSEEK_API_KEY 读取）
        model: 模型名称（为空则使用 DEFAULT_MODEL）
        base_url: 自定义 API 地址
        """
        import os

        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self.model = model or self.DEFAULT_MODEL
        self.base_url = base_url or self.API_URL

    @classmethod
    def _check_dependencies(cls) -> None:
        """检查依赖是否可用（仿 bcrypt 的 _load_backend 检测）"""
        if not _HTTPX_AVAILABLE:
            raise ImportError("httpx 未安装，请运行: pip install httpx")

    async def health_check(self) -> bool:
        """检查 API Key 是否配置、连接是否可用"""
        if not self.api_key:
            logger.warning("DeepSeek API Key 未配置")
            return False
        try:
            import httpx

            async with httpx.AsyncClient(timeout=httpx.Timeout(5)) as client:
                r = await client.get(
                    "https://api.deepseek.com/v1/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                return r.status_code == 200
        except Exception:
            return False

    async def generate(self, prompt: str, **kwargs) -> dict[str, Any]:
        """
        调用 DeepSeek API 生成 JSON 内容。

        Args:
            prompt: 详细的生成提示
            **kwargs: temperature, max_tokens 等
        """
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
                    "content": "你是专业的SEO和网站内容生成助手。严格按照要求的JSON格式输出，不要输出markdown代码块外的内容。",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096),
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30, read=90),
        ) as client:
            r = await client.post(self.base_url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()

        content = data["choices"][0]["message"]["content"]
        return self._parse_json(content)

    def _parse_json(self, raw: str) -> dict:
        """解析 AI 返回的 JSON（处理可能的 markdown 包裹）"""
        raw = raw.strip()
        # 尝试直接解析
        try:
            return _json.loads(raw)
        except _json.JSONDecodeError:
            pass
        # 尝试提取 markdown 代码块
        for pattern in [r"```json\s*\n(.*?)\n```", r"```\s*\n(.*?)\n```", r"```(.*?)```"]:
            m = re.search(pattern, raw, re.DOTALL)
            if m:
                try:
                    return _json.loads(m.group(1).strip())
                except _json.JSONDecodeError:
                    continue
        # 尝试提取花括号
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                return _json.loads(m.group(0))
            except _json.JSONDecodeError:
                pass
        raise ValueError(f"DeepSeek 返回无法解析为 JSON: {raw[:200]}...")
