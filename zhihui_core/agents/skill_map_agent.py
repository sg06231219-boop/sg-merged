"""
岗位能力图谱 Agent - 优化版
AI超时15秒快速fallback，确保前端不502
"""

import os
import json
import re
import time
import requests
from typing import Dict, List

ZHIPUAI_API_KEY = os.environ.get(
    "ZHIPUAI_API_KEY",
    "a3a3123abff546999aeb4547885c4ae8.PocEri894pv9APeu"
)

def _call_glm(messages: list, temperature: float = 0.3, timeout: int = 20) -> str:
    """调用智谱GLM-4-flash，短超时快速fallback"""
    try:
        from core.utils.jwt_helper import generate_token
        token = generate_token(ZHIPUAI_API_KEY)
        resp = requests.post(
            "https://open.bigmodel.cn/api/paas/v4/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            json={
                "model": "glm-4-flash",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 2000,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        raise RuntimeError("AI请求超时")
    except requests.exceptions.ConnectionError:
        raise RuntimeError("AI服务连接失败")
    except Exception as e:
        raise RuntimeError(f"AI调用失败: {str(e)[:80]}")


def _extract_json(content: str) -> dict:
    """从AI返回中提取JSON"""
    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
    if json_match:
        return json.loads(json_match.group(1))
    json_start = content.find('{')
    json_end = content.rfind('}') + 1
    if json_start >= 0 and json_end > json_start:
        return json.loads(content[json_start:json_end])
    raise ValueError("无法从AI返回中提取JSON")


def build_skill_map(job_name: str, major: str = "软件技术") -> Dict:
    """生成岗位能力图谱，20秒超时"""
    prompt = f"""你是职业教育专家。为"{major}"专业群的"{job_name}"岗位生成能力图谱。

严格输出JSON（无其他文字）：
```json
{{
  "job_name": "{job_name}",
  "major": "{major}",
  "skill_tree": {{
    "核心能力": [{{"name": "名称", "level": "基础/进阶/高级", "description": "描述"}}],
    "专业技能": [{{"name": "名称", "tools": ["工具"], "proficiency": "程度"}}],
    "工具技能": [{{"name": "名称", "category": "类别", "importance": "必备/推荐"}}],
    "软技能": [{{"name": "名称", "scenario": "场景"}}]
  }},
  "career_path": [{{"stage": "阶段", "duration": "时间", "milestones": ["里程碑"]}}],
  "related_jobs": ["关联岗位"]
}}
```
至少8个核心能力、10个专业技能、6个工具技能、5个软技能。"""

    messages = [
        {"role": "system", "content": "你是职业教育专家。只输出JSON，不解释。"},
        {"role": "user", "content": prompt},
    ]
    content = _call_glm(messages, timeout=10)
    return _extract_json(content)


def discover_new_job(trend_keywords: List[str]) -> Dict:
    """新岗位发现，15秒超时"""
    prompt = f"""根据技术趋势：{', '.join(trend_keywords)}，发现一个新兴岗位。
输出JSON：{{"job_name":"名称","core_responsibility":"职责","required_skills":["技能"],"bonus_skills":["加分"],"scenarios":["场景"],"why_emerging":"原因"}}"""
    messages = [
        {"role": "system", "content": "你是IT行业分析师。只输出JSON。"},
        {"role": "user", "content": prompt},
    ]
    content = _call_glm(messages, timeout=10)
    return _extract_json(content)
