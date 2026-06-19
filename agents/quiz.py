"""
分阶测试Agent
生成测试题、评估掌握度、动态调整难度
"""
import json
from agents.base import BaseAgent


class QuizAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="quiz",
            role="分阶测试专家",
            description="生成分阶测试题，评估掌握度，支持动态难度调整"
        )
    
    async def execute(self, knowledge: dict = None, difficulty: str = "medium", **kwargs) -> dict:
        knowledge = knowledge or {}
        title = knowledge.get("title", "编程基础")
        concepts = knowledge.get("concepts", [])
        
        system_prompt = """你是陈姐——某大厂技术面试官，面过2000+候选人。
你不会出"什么是XX"这种侮辱智商的选择题。你出的题会让人想3秒，然后发现：哦，我以为我会了。

⚠️ 禁止出这种题：
- "Python中用什么关键字定义函数？"——这是背API，不是学编程
- "以下哪个是正确的？" + 3个明显荒谬的选项——测的是视力不是理解
- 纯记忆型选择题

你的出题风格：
"下面两段代码功能一样吗？如果不一样，差在哪？"
"这个bug在生产环境跑了3天才被发现——你看得出来吗？"

好的选择题 = 所有选项看起来都有道理 + 但只有真正理解才能选中正确答案

JSON输出：
{
    "quiz_title": "测试标题（不要'XX测试题'——用'来，看看你是真懂还是假懂'这样的）",
    "difficulty": "easy/medium/hard",
    "questions": [
        {
            "id": 1,
            "type": "choice（全部选择题，4个选项）",
            "difficulty": "easy/medium/hard",
            "question": "题目——最好是个小场景或陷阱题",
            "options": ["A. 看起来对但实际错的选项", "B. 正确答案", "C. 常见误解", "D. 另一个看起来对的"],
            "correct": 正确答案在options中的索引(0-3), 
            "trap": "这题的陷阱在哪——为什么有人会选错",
            "interviewer_note": "面试官点评：XX（口语化，说清楚为什么这道题能区分真懂和假懂）",
            "knowledge_point": "考察的知识点"
        }
    ],
    "total_score": 100,
    "passing_score": 60,
    "summary": "50字总结，像一个面试官看完候选人答题后的评价"
}

重要：correct字段必须是0-3的数字(不是ABCD)。题目必须全是choice类型(不要short_answer/coding)。"""
        
        concepts_str = "、".join(concepts) if concepts else "编程基础知识"
        user_prompt = f"""请基于以下学习内容生成分阶测试题：
- 主题：{title}
- 核心概念：{concepts_str}
- 难度级别：{difficulty}

要求：
1. 生成5道题目（2道easy + 2道medium + 1道hard）
2. 包含选择题和简答题
3. 每题标注考察的知识点
4. 提供答案解析"""
        
        try:
            raw = self._call_llm(system_prompt, user_prompt, temperature=0.6)
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            result = json.loads(raw.strip())
        except (json.JSONDecodeError, Exception) as e:
            result = self._fallback_quiz(title, difficulty, str(e))
        
        # 标准化correct字段为数字索引
        for q in result.get("questions", []):
            c = q.get("correct")
            if isinstance(c, str):
                # "A"->0, "B"->1, "C"->2, "D"->3
                if c.upper() in "ABCD":
                    q["correct"] = "ABCD".index(c.upper())
                elif c.isdigit() and 0 <= int(c) <= 3:
                    q["correct"] = int(c)
                else:
                    q["correct"] = 0
            elif isinstance(c, int):
                q["correct"] = max(0, min(3, c))
            else:
                q["correct"] = 0
        
        result["agent"] = self.name
        return result
    
    def _fallback_quiz(self, title: str, difficulty: str, error: str) -> dict:
        return {
            "quiz_title": f"{title}测试题（{difficulty}级）",
            "difficulty": difficulty,
            "questions": [
                {"id": 1, "type": "choice", "difficulty": "easy", "question": "Python中用什么关键字定义函数？", "options": ["function", "def", "func", "define"], "correct": 1, "explanation": "Python使用def关键字定义函数", "knowledge_point": "函数定义"},
                {"id": 2, "type": "choice", "difficulty": "easy", "question": "以下哪个是Python的列表？", "options": ["(1,2,3)", "[1,2,3]", "{1,2,3}", "<1,2,3>"], "correct": 1, "explanation": "Python列表使用方括号[]", "knowledge_point": "数据类型"},
                {"id": 3, "type": "choice", "difficulty": "medium", "question": "Python中变量的作用域是指什么？", "options": ["变量存储的数据类型", "变量能被访问的代码范围", "变量的命名规则", "变量的内存地址"], "correct": 1, "explanation": "作用域决定了变量在哪些代码区域可以被访问", "knowledge_point": "作用域"},
                {"id": 4, "type": "choice", "difficulty": "medium", "question": "Python中__init__方法的作用是？", "options": ["销毁对象", "初始化对象", "继承父类", "重载运算符"], "correct": 1, "explanation": "__init__是构造方法，用于初始化对象", "knowledge_point": "面向对象"},
                {"id": 5, "type": "choice", "difficulty": "hard", "question": "以下哪个表达式能正确返回列表中所有偶数的平方？", "options": ["[x^2 for x in lst if x%2==0]", "[x**2 for x in lst if x%2==0]", "filter(lambda x:x%2==0, lst)", "list(map(lambda x:x*x, lst))"], "correct": 1, "explanation": "列表推导式 [x**2 for x in lst if x%2==0] 正确筛选偶数并求平方", "knowledge_point": "列表推导式+条件筛选"},
            ],
            "total_score": 100,
            "passing_score": 60,
            "summary": f"共5题，覆盖{title}的基础到进阶知识点",
            "fallback": True,
            "error": error,
        }
