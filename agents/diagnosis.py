"""
学情诊断Agent
分析学习者背景，生成知识画像，定位知识盲区
输出：学习水平评估、知识盲区列表、推荐学习路径
"""
import json
from agents.base import BaseAgent


class DiagnosisAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="diagnosis",
            role="学情诊断专家",
            description="分析学习者背景，生成知识画像，精准定位知识盲区"
        )
    
    async def execute(self, profile: dict = None, **kwargs) -> dict:
        profile = profile or {}
        background = profile.get("background", "未说明")
        experience = profile.get("experience", "无")
        goal = profile.get("goal", "学习AI/编程技能")
        level = profile.get("level", "beginner")
        
        system_prompt = """你是林教授——一个教了18年编程的大学老师，看过了太多学习者犯同样的错。
你说话直白、不留情面，但每次批评都一针见血。你最烦的就是"多练习就好"这种正确的废话。

⚠️ 绝对禁止：
- "首先...其次...最后..."的三段式八股
- "需要加强XX基础"之类不痛不痒的套话
- "综上所述"、"在XX领域"、"系统性地"

你说话的方式像这样：
"你的问题不是'基础知识薄弱'——谁的基础不薄弱了？你的真实问题是：学了半年Python还在用print调试，这说明你根本没见过真实的工程代码长什么样。"

先在心里分析（别写出来）：
1. 这个人说的"学习目标"和ta的"实际水平"之间最大的鸿沟在哪？
2. 如果我只能给ta一条建议，这条建议是什么？
3. ta最可能在哪个环节放弃？为什么？

然后以JSON格式给出诊断：
{
    "learner_level": "beginner/intermediate/advanced",
    "level_score": 0-100,
    "raw_truth": "别客气，一针见血地指出ta真正的弱点（50字以内）",
    "strengths": ["不是优点列表，是ta已经有的、可以马上转化为学习杠杆的东西"],
    "blind_spots": ["每个盲区请用'你不知道你不知道XX'的格式，点出元认知层面的盲区"],
    "focus_topic": "最该优先攻克的主题（只要一个，多个等于没说）",
    "red_flag": "如果我最多只能给你一条建议：XX（直接、尖锐、像朋友劝你）",
    "learning_path": [
        {"phase": "阶段名（不要叫'基础入门'这种——叫'第一拳：打碎XX幻觉'这种实在的）", "topics": ["主题"], "estimated_hours": 学时, "why_this_matters": "做这件事到底有什么用"}
    ],
    "summary": "用一句话概括：你是谁 + 你最大的坑是什么 + 怎么爬出来（40字内）"
}"""
        
        user_prompt = f"""又来一个学习者，帮我看看——
背景：{background}
编程经验：{experience}
学习目标：{goal}
自评水平：{level}

别给ta什么"需要系统学习"的废话，说点ta真正需要听到的。
JSON输出。"""
        
        try:
            raw = self._call_llm(system_prompt, user_prompt, temperature=0.8)
            # 尝试解析JSON
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            result = json.loads(raw.strip())
        except (json.JSONDecodeError, Exception) as e:
            result = self._fallback_diagnosis(profile, str(e))
        
        result["agent"] = self.name
        return result
    
    def _fallback_diagnosis(self, profile: dict, error: str) -> dict:
        """LLM失败时的兜底诊断 - 基于profile生成真实感诊断"""
        level = profile.get("level", "beginner")
        background = profile.get("background", "")
        goal = profile.get("goal", "学习AI/编程技能")
        
        level_map = {
            "beginner": {"level_score": 25, "strengths": ["学习热情", "基础认知"], "blind_spots": ["编程基础", "算法思维", "数据结构", "开发工具"]},
            "intermediate": {"level_score": 55, "strengths": ["编程基础", "逻辑思维", "基本调试"], "blind_spots": ["系统设计", "性能优化", "AI算法", "工程规范"]},
            "advanced": {"level_score": 80, "strengths": ["项目经验", "系统设计", "代码优化"], "blind_spots": ["前沿AI技术", "大规模系统", "底层原理"]},
        }
        info = level_map.get(level, level_map["beginner"])
        
        # 从background提取潜在信息
        if "python" in background.lower():
            info["strengths"].append("Python语法基础")
            if "AI" in info["blind_spots"]: info["blind_spots"].remove("AI")
        if "数学" in background or "统计" in background:
            info["strengths"].append("数学基础")
        
        focus = info["blind_spots"][0] if info["blind_spots"] else "编程基础"
        # 从goal调整focus
        if "AI" in goal or "机器学习" in goal: focus = "AI算法与框架"
        elif "web" in goal.lower() or "前端" in goal: focus = "Web开发技术"
        elif "数据" in goal: focus = "数据分析与处理"
        
        return {
            "learner_level": level,
            "level_score": info["level_score"],
            "strengths": info["strengths"][:5],
            "blind_spots": info["blind_spots"][:5],
            "focus_topic": focus,
            "learning_path": [
                {"phase": "基础入门", "topics": info["blind_spots"][:2], "estimated_hours": 20},
                {"phase": "核心提升", "topics": [focus, "项目实践"], "estimated_hours": 30},
                {"phase": "综合应用", "topics": ["实战项目", "代码优化"], "estimated_hours": 25},
            ],
            "summary": f"学习者自评{level}级，核心强项{info['strengths'][0] if info['strengths'] else '待发掘'}，建议从{focus}开始系统学习",
            "fallback": True,
            "error": error,
        }
