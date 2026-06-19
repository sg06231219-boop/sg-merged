"""
个性化学习路径 Agent - 优化版
AI超时10秒快速fallback，避免Render 30秒请求限制
"""

import os
import json
import re
import requests
from typing import Dict, List

ZHIPUAI_API_KEY = os.environ.get(
    "ZHIPUAI_API_KEY",
    "a3a3123abff546999aeb4547885c4ae8.PocEri894pv9APeu"
)

def _call_glm(messages: list, temperature: float = 0.3, timeout: int = 20) -> str:
    """调用智谱GLM-4-flash"""
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


def diagnose_learning(user_profile: Dict, target_job: str) -> Dict:
    """学情诊断，10秒超时"""
    prompt = f"""分析学生画像与目标岗位匹配度。

学生画像：{json.dumps(user_profile, ensure_ascii=False)}
目标岗位：{target_job}

输出JSON：{{"match_score":75,"mastered_skills":[],"gap_skills":[],"gap_level":{{"核心能力":{{"gap":2,"detail":"描述"}},"专业技能":{{"gap":1,"detail":"描述"}},"工具技能":{{"gap":1,"detail":"描述"}},"软技能":{{"gap":1,"detail":"描述"}}}},"diagnosis_summary":"结论","priority_skills":[],"estimated_hours":320}}"""
    messages = [
        {"role": "system", "content": "你是职业教育诊断专家。只输出JSON。"},
        {"role": "user", "content": prompt},
    ]
    content = _call_glm(messages, timeout=10)
    return _extract_json(content)


def generate_learning_path(diagnosis: Dict, target_job: str, weeks: int = 12) -> Dict:
    """生成学习路径，10秒超时"""
    w3 = max(weeks // 3, 1)
    w23 = max(weeks * 2 // 3, w3 + 1)
    prompt = f"""基于诊断结果为「{target_job}」制定{weeks}周学习路径。

诊断：{json.dumps(diagnosis, ensure_ascii=False)}

输出JSON：{{"total_weeks":{weeks},"path":[{{"phase":"阶段","weeks":"时间","tasks":[{{"task_name":"任务","knowledge_points":["知识点"],"practice":"实践"}}],"milestone":"里程碑"}}],"growth_trajectory":[{{"week":0,"score":30}},{{"week":{w3},"score":55}},{{"week":{w23},"score":75}},{{"week":{weeks},"score":85}}]}}"""
    messages = [
        {"role": "system", "content": "你是课程设计专家。只输出JSON。"},
        {"role": "user", "content": prompt},
    ]
    content = _call_glm(messages, timeout=10)
    return _extract_json(content)
