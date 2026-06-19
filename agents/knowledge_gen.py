"""
领域知识生成Agent
基于学情诊断结果，从知识库检索相关知识，生成个性化学习内容
输出：定制化学习资源、知识溯源引用
"""
import json
import os
from agents.base import BaseAgent


class KnowledgeGenAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="knowledge_gen",
            role="领域知识生成专家",
            description="基于学情诊断和知识库，生成个性化学习内容，标注知识溯源"
        )
        self.kb_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "knowledge_base"
        )
    
    async def execute(self, diagnosis: dict = None, revision_hints: list = None, **kwargs) -> dict:
        diagnosis = diagnosis or {}
        focus_topic = diagnosis.get("focus_topic", "Python编程基础")
        level = diagnosis.get("learner_level", "beginner")
        blind_spots = diagnosis.get("blind_spots", [])
        
        # 从知识库加载相关内容
        kb_content = self._load_knowledge(focus_topic)
        
        revision_note = ""
        if revision_hints:
            revision_note = f"\n\n⚠️ 审核Agent指出以下问题需要修正：{json.dumps(revision_hints, ensure_ascii=False)}\n请针对这些问题重新生成内容。"
        
        system_prompt = """你是阿坤——在GitHub上混了10年的野生程序员，从写bug到给开源项目提PR，什么弯路都走过。
你对大学教材深恶痛绝——"那些书把活的知识写死了"。
你的信条：一个概念如果不能用一个6岁小孩都能懂的类比讲清楚，就说明你没真懂。

⚠️ 绝对禁止：
- "首先我们要了解XX的定义"——没人想先看定义
- Markdown标题叫"一、概述"、"二、核心内容"——这种结构直接删掉重写
- "在实际开发中"、"有助于提升"——这些都是空话，换成具体场景名
- 引用的代码不要写import xx这种占位符，写真实能跑的代码

你说话的方式就像：
"今天不讲虚的。就说一个事——Python里的list到底为什么有时候'丢'元素。很多人觉得list简单，但90%的人栽在同一个坑上..."

内容结构：用反直觉例子开头→用类比讲核心原理→给一个"教科书不会告诉你的事实"→代码注释要有性格

JSON输出：
{
    "title": "别用'XX基础教程'这种标题——用'XX：90%的人都搞错了的那个概念'这种真想让人点进去的",
    "hook": "反直觉引子（1-3句，让人想继续读）",
    "content": "完整内容(Markdown，800-1500字，像博客不像教材)",
    "hidden_truth": "官方文档不会告诉你的一个事实或技巧",
    "source_refs": [{"id":"引用","source":"来源文件","type":"[教材]|[官方]|[论文]|[实践]","relevance":"说明"}],
    "concepts": ["核心概念——用口语化命名"],
    "examples": ["实操示例"],
    "extensions": ["想继续深入？看这里——给具体链接/书名"],
    "summary": "像朋友推荐文章那样写50字摘要，别像论文"
}"""
        
        kb_summary = kb_content[:1500] if kb_content else '暂无'
        user_prompt = f"""请为以下学习者生成个性化学习内容：

学情诊断：
- 学习水平：{level}
- 重点主题：{focus_topic}
- 知识盲区：{blind_spots}

参考素材：
{kb_summary}
{revision_note}"""
        
        try:
            raw = self._call_llm(system_prompt, user_prompt, temperature=0.8)
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            result = json.loads(raw.strip())
        except (json.JSONDecodeError, Exception) as e:
            result = self._fallback_knowledge(focus_topic, level, str(e))
        
        result["agent"] = self.name
        return result
    
    def _load_knowledge(self, topic: str) -> str:
        """从知识库加载相关内容，关键词+内容双匹配"""
        results = []
        topic_lower = topic.lower()
        topic_keywords = set(topic_lower.replace('_', ' ').replace('-', ' ').split())
        try:
            files = sorted(f for f in os.listdir(self.kb_path) if f.endswith(".md"))
        except Exception:
            return ""
        
        for fname in files:
            fpath = os.path.join(self.kb_path, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue
            # 文件名匹配
            fname_base = fname.replace('.md', '').replace('_', ' ').lower()
            name_match = any(kw in fname_base for kw in topic_keywords)
            # 内容匹配
            content_lower = content[:3000].lower()
            content_match = sum(1 for kw in topic_keywords if kw in content_lower)
            
            if name_match or content_match >= 1:
                results.append((name_match * 10 + content_match, content))
        
        if results:
            results.sort(key=lambda x: -x[0])
            return results[0][1][:3000]  # 最相关的，截取前3000字
        
        # 没找到则返回所有知识库摘要
        all_summaries = []
        for fname in files[:3]:
            fpath = os.path.join(self.kb_path, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    all_summaries.append(f"[{fname}]\n" + f.read()[:500])
            except Exception:
                continue
        return "\n---\n".join(all_summaries) if all_summaries else ""
    
    def _fallback_knowledge(self, topic: str, level: str, error: str) -> dict:
        """兜底生成 - 基于topic和level生成更真实的学习内容"""
        # 根据主题生成针对性内容
        topic_content = {
            "Python": f"""## Python编程基础

### 核心概念
Python是一种高级编程语言，以简洁优雅的语法著称。它支持面向对象、函数式和过程式编程范式。

### 关键语法
- **变量与数据类型**：Python是动态类型语言，变量无需声明类型
  ```python
  name = "Alice"  # 字符串
  age = 25        # 整数
  scores = [90, 85, 92]  # 列表
  ```
- **函数定义**：使用`def`关键字
  ```python
  def greet(name, greeting="Hello"):
      return f"{greeting}, {name}!"
  ```
- **列表推导式**：简洁的数据变换语法
  ```python
  evens = [x for x in range(20) if x % 2 == 0]
  ```

### 实践要点
1. 使用虚拟环境管理依赖（`python -m venv`）
2. 熟悉pip包管理器
3. 掌握常用内置函数：`map()`, `filter()`, `zip()`""",
            "AI": f"""## AI开发入门

### 机器学习基础
机器学习是AI的核心分支，通过数据训练模型来实现预测和决策。

### 核心工具链
- **NumPy**：高性能数值计算
  ```python
  import numpy as np
  arr = np.array([1, 2, 3])
  print(arr.mean())  # 2.0
  ```
- **Pandas**：数据处理与分析
  ```python
  import pandas as pd
  df = pd.read_csv('data.csv')
  df.describe()  # 统计摘要
  ```
- **Scikit-learn**：经典机器学习
  ```python
  from sklearn.model_selection import train_test_split
  from sklearn.linear_model import LogisticRegression
  ```

### 学习路径
1. 数据处理 → 2. 特征工程 → 3. 模型训练 → 4. 评估优化""",
        }
        
        # 选择最匹配的内容模板
        content = topic_content.get("Python", "")
        for key, val in topic_content.items():
            if key.lower() in topic.lower():
                content = val
                break
        if not content:
            content = f"""## {topic}学习指南

### 核心概念
{topic}是当前技术领域的重要方向，需要系统性的学习和实践。

### 学习要点
1. **基础理论**：理解核心原理和关键概念
2. **动手实践**：通过项目练习巩固知识
3. **进阶提升**：深入理解底层机制和最佳实践

### 实践建议
- 从简单示例开始，逐步增加复杂度
- 多阅读官方文档和优质教程
- 参与开源项目提升实战能力"""

        level_suffix = {"beginner": "（入门级）", "intermediate": "（进阶级）", "advanced": "（高级）"}
        return {
            "title": f"{topic} - {level}级学习内容{level_suffix.get(level, '')}",
            "content": content,
            "source_refs": [
                {"id": "KB001", "source": "python_basics.md", "type": "[教材]", "relevance": "核心参考"},
                {"id": "KB002", "source": "ai_basics.md", "type": "[实践]", "relevance": "应用参考"},
            ],
            "concepts": [f"{topic}基本概念", f"{topic}核心原理", "实践方法论"],
            "examples": [f"{topic}入门示例", f"{topic}进阶练习"],
            "extensions": [f"{topic}进阶资料", "相关开源项目"],
            "summary": f"面向{level}级学习者的{topic}个性化内容，涵盖概念讲解与实操示例",
            "fallback": True,
            "error": error,
        }
