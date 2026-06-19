"""
协同调度Agent - 核心编排器
实现"诊断→生成→审核→测试→迭代"全流程闭环
支持辩论机制:生成Agent与审核Agent交叉验证
"""
import asyncio
import json
import time
from typing import AsyncGenerator, Dict, Any, Optional


class Orchestrator:
    """多智能体协同调度器"""

    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.debate_rounds = 2

    def register(self, name: str, agent):
        self.agents[name] = agent

    def list_agents(self) -> list:
        return [a.info() for a in self.agents.values()]

    async def run_agent(self, name: str, **kwargs) -> dict:
        agent = self.agents.get(name)
        if not agent:
            return {"error": f"Agent '{name}' not found"}
        start = time.time()
        result = await agent.execute(**kwargs)
        elapsed = round(time.time() - start, 2)
        result["_meta"] = {
            "agent": name,
            "role": agent.role,
            "elapsed_seconds": elapsed,
        }
        agent.last_result = result
        return result

    async def run_full_pipeline(self, profile: dict) -> dict:
        pipeline_result = {
            "learner_profile": profile,
            "steps": [],
            "final_output": {},
        }

        diagnosis = await self.run_agent("diagnosis", profile=profile)
        pipeline_result["steps"].append({"step": 1, "agent": "diagnosis", "status": "completed", "summary": diagnosis.get("summary", "")})

        knowledge = await self.run_agent("knowledge_gen", diagnosis=diagnosis)
        pipeline_result["steps"].append({"step": 2, "agent": "knowledge_gen", "status": "completed", "summary": knowledge.get("summary", "")})

        review_result = await self._debate_loop(content=knowledge.get("content", ""), source_refs=knowledge.get("source_refs", []))
        pipeline_result["steps"].append({"step": 3, "agent": "reviewer", "status": "completed", "debate_rounds": review_result.get("debate_rounds", 0), "hallucination_score": review_result.get("hallucination_score", 0), "summary": review_result.get("summary", "")})

        if review_result.get("needs_revision", False):
            knowledge = await self.run_agent("knowledge_gen", diagnosis=diagnosis, revision_hints=review_result.get("issues", []))
            pipeline_result["steps"].append({"step": "3b", "agent": "knowledge_gen", "status": "revised", "summary": "根据审核意见修订内容"})

        practice = await self.run_agent("practice_guide", topic=diagnosis.get("focus_topic", "Python编程基础"), level=profile.get("level", "beginner"))
        pipeline_result["steps"].append({"step": 4, "agent": "practice_guide", "status": "completed", "summary": practice.get("summary", "")})

        quiz = await self.run_agent("quiz", knowledge=knowledge, difficulty=profile.get("level", "medium"))
        pipeline_result["steps"].append({"step": 5, "agent": "quiz", "status": "completed", "summary": quiz.get("summary", "")})

        # Step 6: 动态迭代
        iteration = await self.run_agent("iteration", quiz_result=quiz, diagnosis=diagnosis, knowledge=knowledge)
        pipeline_result["steps"].append({"step": 6, "agent": "iteration", "status": "completed", "decision": iteration.get("decision", ""), "summary": iteration.get("summary", "")})

        # Step 7: 启发式导学
        socratic = await self.run_agent("socratic", knowledge=knowledge, mode="embed_questions")
        pipeline_result["steps"].append({"step": 7, "agent": "socratic", "status": "completed", "summary": socratic.get("summary", "")})

        pipeline_result["final_output"] = {"diagnosis": diagnosis, "knowledge": knowledge, "review": review_result, "practice": practice, "quiz": quiz, "iteration": iteration, "socratic": socratic}
        return pipeline_result

    async def _debate_loop(self, content: str, source_refs: list, max_rounds: int = 2, min_rounds: int = 2, event_callback=None) -> dict:
        current_content = content
        debate_log = []

        for round_num in range(1, max_rounds + 1):
            review = await self.run_agent("reviewer", content=current_content, source_refs=source_refs, debate_round=round_num)
            hallucination_score = review.get("hallucination_score", 50)
            issues = review.get("issues", [])
            debate_log.append({"round": round_num, "reviewer_verdict": review.get("verdict", "uncertain"), "hallucination_score": hallucination_score, "issues_count": len(issues)})

            if event_callback:
                await event_callback({"type": "debate_round", "round": round_num, "verdict": review.get("verdict", "uncertain"), "hallucination_score": hallucination_score, "issues_count": len(issues)})

            # 强制至少跑完min_rounds轮辩论，才允许提前退出
            if hallucination_score < 20 and round_num >= min_rounds:
                review["debate_rounds"] = round_num
                review["debate_log"] = debate_log
                review["needs_revision"] = False
                return review

            # 修订内容后继续下一轮辩论
            if round_num < max_rounds:
                revision_hints = [i.get("description", "") for i in issues if isinstance(i, dict)]
                revised = await self.run_agent("knowledge_gen", diagnosis={}, revision_hints=revision_hints)
                current_content = revised.get("content", current_content)

        review["debate_rounds"] = max_rounds
        review["debate_log"] = debate_log
        review["needs_revision"] = hallucination_score >= 40
        return review

    async def run_streaming(self, profile: dict) -> AsyncGenerator[dict, None]:
        """
        流式输出调度过程--直接顺序执行并逐步yield事件
        不再用Queue,避免事件循环阻塞问题
        """
        try:
            # Step 1: 学情诊断
            yield {"type": "agent_start", "agent": "diagnosis", "step": 1}
            diagnosis = await self.run_agent("diagnosis", profile=profile)
            yield {"type": "agent_done", "agent": "diagnosis", "step": 1, "result": diagnosis}

            # Step 2: 知识生成
            yield {"type": "agent_start", "agent": "knowledge_gen", "step": 2}
            knowledge = await self.run_agent("knowledge_gen", diagnosis=diagnosis)
            yield {"type": "agent_done", "agent": "knowledge_gen", "step": 2, "result": knowledge}

            # Step 3: 审核辩论
            yield {"type": "agent_start", "agent": "reviewer", "step": 3}

            # 内联辩论循环,直接yield辩论事件
            # 强制至少2轮辩论，确保辩论机制真正运行
            debate_log = []
            current_content = knowledge.get("content", "")
            source_refs = knowledge.get("source_refs", [])
            review = None
            min_rounds = 2  # 至少2轮辩论

            for round_num in range(1, self.debate_rounds + 1):
                review = await self.run_agent("reviewer", content=current_content, source_refs=source_refs, debate_round=round_num)
                hallucination_score = review.get("hallucination_score", 50)
                issues = review.get("issues", [])
                debate_log.append({"round": round_num, "reviewer_verdict": review.get("verdict", "uncertain"), "hallucination_score": hallucination_score, "issues_count": len(issues)})

                yield {"type": "debate_round", "round": round_num, "verdict": review.get("verdict", "uncertain"), "hallucination_score": hallucination_score, "issues_count": len(issues)}

                # 只有跑完至少min_rounds轮且分数足够低才提前退出
                if hallucination_score < 20 and round_num >= min_rounds:
                    review["debate_rounds"] = round_num
                    review["debate_log"] = debate_log
                    review["needs_revision"] = False
                    break

                # 修订内容后继续下一轮辩论
                if round_num < self.debate_rounds:
                    revision_hints = [i.get("description", "") for i in issues if isinstance(i, dict)]
                    revised = await self.run_agent("knowledge_gen", diagnosis=diagnosis, revision_hints=revision_hints)
                    current_content = revised.get("content", current_content)
                    yield {"type": "agent_start", "agent": "knowledge_gen", "step": f"3r{round_num}"}
                    yield {"type": "agent_done", "agent": "knowledge_gen", "step": f"3r{round_num}", "result": revised}
            else:
                # 所有辩论轮次用完
                review["debate_rounds"] = self.debate_rounds
                review["debate_log"] = debate_log
                review["needs_revision"] = hallucination_score >= 40

            yield {"type": "agent_done", "agent": "reviewer", "step": 3, "result": review}

            # 如果需要修订
            if review.get("needs_revision", False):
                yield {"type": "agent_start", "agent": "knowledge_gen", "step": "3b"}
                knowledge = await self.run_agent("knowledge_gen", diagnosis=diagnosis, revision_hints=review.get("issues", []))
                yield {"type": "agent_done", "agent": "knowledge_gen", "step": "3b", "result": knowledge}

            # Step 4: 实操指南
            yield {"type": "agent_start", "agent": "practice_guide", "step": 4}
            practice = await self.run_agent("practice_guide", topic=diagnosis.get("focus_topic", "Python编程基础"), level=profile.get("level", "beginner"))
            yield {"type": "agent_done", "agent": "practice_guide", "step": 4, "result": practice}

            # Step 5: 分阶测试
            yield {"type": "agent_start", "agent": "quiz", "step": 5}
            quiz = await self.run_agent("quiz", knowledge=knowledge, difficulty=profile.get("level", "medium"))
            yield {"type": "agent_done", "agent": "quiz", "step": 5, "result": quiz}

            # Step 6: 动态迭代决策(基于测试结果的反馈闭环)
            yield {"type": "agent_start", "agent": "iteration", "step": 6}
            iteration = await self.run_agent("iteration", quiz_result=quiz, diagnosis=diagnosis, knowledge=knowledge)
            yield {"type": "agent_done", "agent": "iteration", "step": 6, "result": iteration}

            # 如果迭代决策建议简化或进阶,生成适配内容
            if iteration.get("decision") in ("simplify", "advance"):
                yield {"type": "agent_start", "agent": "knowledge_gen", "step": "6b"}
                adjusted_level = "beginner" if iteration["decision"] == "simplify" else "advanced"
                knowledge = await self.run_agent("knowledge_gen", diagnosis={**diagnosis, "learner_level": adjusted_level})
                yield {"type": "agent_done", "agent": "knowledge_gen", "step": "6b", "result": knowledge}

            # Step 7: 启发式导学(嵌入追问节点)
            yield {"type": "agent_start", "agent": "socratic", "step": 7}
            socratic = await self.run_agent("socratic", knowledge=knowledge, mode="embed_questions")
            yield {"type": "agent_done", "agent": "socratic", "step": 7, "result": socratic}

            yield {"type": "pipeline_done", "result": {"diagnosis": diagnosis, "knowledge": knowledge, "review": review, "practice": practice, "quiz": quiz, "iteration": iteration, "socratic": socratic}}

        except Exception as e:
            yield {"type": "error", "message": str(e)}
