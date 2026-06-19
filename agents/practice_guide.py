"""
实操指南Agent
生成动手练习、项目脚手架、代码示例
"""
import json
from agents.base import BaseAgent


class PracticeGuideAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="practice_guide",
            role="实操指南生成专家",
            description="生成代码练习、项目脚手架、分步实操指南"
        )
    
    async def execute(self, topic: str = "", level: str = "beginner", **kwargs) -> dict:
        system_prompt = """你是大刘——在BAT干了12年的老程序员，带过30多个实习生。
你不讲"最佳实践"——你讲"血泪教训"。你教的东西都是自己或同事踩坑踩出来的。

⚠️ 绝对禁止：
- "第一步：环境准备"——烦不烦？要装什么环境一句话说完
- "第二步：编写代码"——这不是步骤，是废话
- 代码注释写"# 定义一个变量"——这种注释删掉，写"# 注意：这里如果用list会慢10倍"这种有用的
- "建议多加练习"——说具体练什么

你的实操指南风格：
"别直接上手写代码。先想3分钟——你要处理的数据长什么样？如果数据量突然变100倍，你的方案还撑得住吗？想清楚了再往下看。"

每步必须包含：
- 真实代码（能跑，不是示意代码）
- "我当年掉过的坑"（一个具体的、血的教训）
- 如果不做这步会怎样（后果前置）

JSON输出：
{
    "title": "指南标题——要有动作感，像'手把手：用XX解决YY的ZZ个坑'",
    "difficulty": "beginner/intermediate/advanced",
    "estimated_time": "预计时间（分钟）",
    "steps": [
        {"step": 1, "title": "步骤名（有动作感）", "why": "为什么要做这步——后果前置", "description": "详细说明", "code": "真实可运行代码", "pitfall": "我踩过的坑：XX", "tip": "一句话技巧"}
    ],
    "project_idea": "不是'做一个XX系统'——而是'做一个具体到能用的小工具，比如XX'",
    "common_mistakes": ["常见错误——每个都用'我见过有人XX然后YY'的叙事"],
    "summary": "50字总结，像同事交接工作时说的话"
}"""
        
        user_prompt = f"""请为{level}级学习者生成关于「{topic}」的实操指南：
- 包含3-5个递进式步骤
- 每步附代码示例
- 包含一个综合项目建议
- 标注常见易错点"""
        
        try:
            raw = self._call_llm(system_prompt, user_prompt, temperature=0.7)
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            result = json.loads(raw.strip())
        except (json.JSONDecodeError, Exception) as e:
            result = self._fallback_practice(topic, level, str(e))
        
        result["agent"] = self.name
        return result
    
    def _fallback_practice(self, topic: str, level: str, error: str) -> dict:
        return {
            "title": f"{topic}实操指南（{level}级）",
            "difficulty": level,
            "estimated_time": "30-60分钟",
            "steps": [
                {"step": 1, "title": "环境准备", "description": f"安装{topic}所需的开发环境和工具", "code": "# 安装示例\npip install python", "tip": "确保Python版本≥3.8"},
                {"step": 2, "title": "基础练习", "description": f"完成{topic}的基本功能实现", "code": "# 基础代码示例\nprint('Hello, World!')", "tip": "注意缩进和语法"},
                {"step": 3, "title": "进阶挑战", "description": "扩展功能，加深理解", "code": "# 进阶代码\n# TODO: 实现更多功能", "tip": "尝试自己思考和实现"},
            ],
            "project_idea": f"构建一个完整的{topic}项目，整合所有学到的知识",
            "common_mistakes": ["忽略异常处理", "变量命名不规范", "缺少注释"],
            "summary": f"面向{level}级学习者的{topic}实操指南",
            "fallback": True,
            "error": error,
        }
