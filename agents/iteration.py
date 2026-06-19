"""
动态迭代Agent
根据学习者反馈（如答题正确率），协同决策是否"降维解释"或"进阶挑战"
实现"交互反馈→动态决策更新"闭环
"""
import json
from agents.base import BaseAgent


class IterationAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="iteration",
            role="动态迭代决策专家",
            description="根据学习反馈动态调整内容难度，实现降维解释或进阶挑战"
        )
    
    async def execute(
        self,
        quiz_result: dict = None,
        diagnosis: dict = None,
        knowledge: dict = None,
        **kwargs
    ) -> dict:
        quiz_result = quiz_result or {}
        diagnosis = diagnosis or {}
        knowledge = knowledge or {}
        
        # 计算正确率
        questions = quiz_result.get("questions", [])
        user_answers = quiz_result.get("user_answers", {})
        correct_count = 0
        total = len(questions)
        
        for q in questions:
            qid = str(q.get("id", ""))
            if qid in user_answers:
                if user_answers[qid] == q.get("correct", ""):
                    correct_count += 1
        
        accuracy = (correct_count / total * 100) if total > 0 else 0
        
        # 根据正确率决定策略
        if accuracy < 60:
            strategy = "simplify"
            strategy_label = "降维解释"
            reason = f"正确率仅{accuracy:.0f}%，需大幅降低难度，补充基础知识"
        elif accuracy < 80:
            strategy = "consolidate"
            strategy_label = "巩固强化"
            reason = f"正确率{accuracy:.0f}%，基本掌握但存在薄弱点，针对性巩固"
        else:
            strategy = "advance"
            strategy_label = "进阶挑战"
            reason = f"正确率{accuracy:.0f}%，掌握良好，可进入更高难度内容"
        
        # 调用LLM生成具体的迭代建议
        system_prompt = """你是赵教练——你不教技术，你教人怎么学。
你见过太多人：学了3个月原地踏步、刷了200道题不知道在刷什么、报了班学完就忘。
你的价值不是给出"正确答案"——任何人都能说"多练练"。你的价值是看穿学习者的瓶颈点在哪，然后给出一个具体的、可立刻执行的动作。

⚠️ 禁止：
- 三天打鱼两天晒网是对的，但直接说这句话没用
- "建议加强XX基础"——这也太宽了，说：明天花1小时把XX做一遍
- "持续学习"——这是浪费时间的话

你的风格：
"你的正确率60%，但真正的问题是——答错的3道题全是同一类问题（XX理解不够）。补那个，别补别的。"
"我让你暂时别学XX了，先把YY啃透。你这周只做一件事：ZZ。"

决策逻辑（先思考再输出）：
1. 正确率<60%→必须降维，但不是退回基础——是退到"这个知识点用更简单的语言讲"
2. 60-80%→不巩固了，找出答错题的知识点，集中轰炸
3. >80%→不要泛泛说"进阶"，说下一个具体学什么

JSON输出：
{
    "decision": "simplify/consolidate/advance",
    "decision_label": "降维解释/定点突破/进阶挑战",
    "reason": "决策理由——用'你现在的核心问题是XX，因为YY'的句式",
    "one_thing": "只做一件事：XX（一个具体动作，明天就能做的）",
    "adjustments": {
        "difficulty_shift": -2到+2,
        "focus_topics": ["只列1-2个，多了没用"],
        "skip_topics": ["暂时放掉这些"],
        "new_approach": "换个方式学——具体怎么换"
    },
    "next_steps": [
        {"step": 1, "action": "具体行动", "agent": "负责Agent", "description": "详细说明——要有量化（多长时间、做多少）"}
    ],
    "summary": "30字迭代总结，像教练说的一句话"
}"""
        
        user_prompt = f"""请根据以下测试结果做出迭代决策：

学情诊断：
- 学习水平：{diagnosis.get('learner_level', 'unknown')}
- 知识盲区：{diagnosis.get('blind_spots', [])}

测试结果：
- 总题数：{total}
- 答对题数：{correct_count}
- 正确率：{accuracy:.1f}%
- 当前策略：{strategy_label}

已学内容主题：{knowledge.get('title', '未知')}
核心概念：{knowledge.get('concepts', [])}

请给出精准的迭代学习建议。"""
        
        try:
            raw = self._call_llm(system_prompt, user_prompt, temperature=0.6)
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            result = json.loads(raw.strip())
        except (json.JSONDecodeError, Exception) as e:
            result = self._fallback_iteration(accuracy, strategy, strategy_label, reason, str(e))
        
        result["agent"] = self.name
        result["accuracy"] = round(accuracy, 1)
        result["correct_count"] = correct_count
        result["total_questions"] = total
        return result
    
    def _fallback_iteration(self, accuracy, strategy, label, reason, error):
        adjustments = {
            "simplify": {"difficulty_shift": -2, "focus_topics": ["基础概念复习", "关键知识点重讲", "简单示例练习"], "skip_topics": ["高级特性", "底层原理"], "new_approach": "用更通俗的语言和更多示例讲解，每步附注释说明"},
            "consolidate": {"difficulty_shift": 0, "focus_topics": ["薄弱环节强化", "易错点梳理", "综合练习"], "skip_topics": [], "new_approach": "针对性补充练习和讲解，增加知识关联图"},
            "advance": {"difficulty_shift": +2, "focus_topics": ["进阶技术", "实战项目", "底层原理"], "skip_topics": ["已掌握的基础知识"], "new_approach": "引入更高难度的概念和项目实践，关注性能和设计模式"},
        }
        return {
            "decision": strategy,
            "decision_label": label,
            "reason": reason,
            "adjustments": adjustments.get(strategy, adjustments["consolidate"]),
            "next_steps": [
                {"step": 1, "action": f"执行{label}策略", "agent": "knowledge_gen", "description": reason},
                {"step": 2, "action": "生成适配内容", "agent": "practice_guide", "description": f"根据{label}策略生成对应难度的实操练习"},
            ],
            "summary": f"正确率{accuracy:.0f}%，建议{label}，{reason}",
            "fallback": True,
            "error": error,
        }
