"""ReAct Agent 实现"""
from typing import Dict, Any, List, Optional
from langchain_core.documents import Document
from .reasoning import ReasoningEngine
from .action_executor import ActionExecutor
from ..utils.config import get_config
import logging

logger = logging.getLogger(__name__)


class ReActAgent:
    """ReAct Agent，实现思考-行动-观察循环"""

    def __init__(
        self,
        reasoning_engine: Optional[ReasoningEngine] = None,
        action_executor: Optional[ActionExecutor] = None,
        config=None,
    ):
        """
        初始化 ReAct Agent

        Args:
            reasoning_engine: 推理引擎
            action_executor: 动作执行器
            config: 配置对象
        """
        if config is None:
            config = get_config()

        self.config = config
        self.agent_config = config.agent

        self.reasoning_engine = reasoning_engine or ReasoningEngine(config)
        self.action_executor = action_executor or ActionExecutor(config=config)

        self.max_iterations = self.agent_config.max_iterations
        self.confidence_threshold = self.agent_config.confidence_threshold
        self.enable_reretrieval = self.agent_config.enable_reretrieval
        self.enable_replanning = self.agent_config.enable_replanning

    async def react_loop(
        self,
        query: str,
        initial_context: Optional[List[Document]] = None,
        memory_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        ReAct 循环执行

        Args:
            query: 查询文本
            initial_context: 初始上下文文档
            memory_context: 记忆上下文

        Returns:
            包含答案和执行历史的字典
        """
        context = initial_context or []
        execution_path = []
        previous_reasoning = None
        best_answer = None
        best_score = 0.0

        for iteration in range(self.max_iterations):
            logger.info(f"ReAct 迭代 {iteration + 1}/{self.max_iterations}")

            # 1. 思考阶段：推理和规划
            reasoning_result = self.reasoning_engine.reason(
                query=query,
                context=context,
                previous_reasoning=previous_reasoning,
            )

            thought = reasoning_result.get("thought", "")
            action = reasoning_result.get("action", "answer")
            action_input = reasoning_result.get("action_input", "")
            confidence = reasoning_result.get("confidence", 0.5)

            # 2. 检查置信度，决定是否需要二次检索
            if (
                self.enable_reretrieval
                and confidence < self.confidence_threshold
                and action == "answer"
                and iteration < self.max_iterations - 1
            ):
                logger.info(f"置信度低 ({confidence:.2f})，触发二次检索")
                
                # 扩大检索范围
                expanded_docs = self.action_executor.expand_retrieval(
                    query=query,
                    original_top_k=len(context) if context else 5,
                    expansion_factor=4,
                )
                
                # 合并上下文
                context.extend(expanded_docs)
                context = self._deduplicate_documents(context)
                
                # 继续循环
                execution_path.append({
                    "iteration": iteration + 1,
                    "thought": thought,
                    "action": "reretrieval",
                    "result": f"扩大检索，新增 {len(expanded_docs)} 个文档",
                    "confidence": confidence,
                })
                continue

            # 3. 执行动作
            action_result = self.action_executor.execute(
                action=action,
                action_input=action_input,
                query=query,
                context=context,
            )

            # 4. 如果是回答动作，验证答案
            if action == "answer":
                answer = action_result.get("result", "")
                
                # 验证答案
                validation = self.reasoning_engine.validate_answer(
                    query=query,
                    reasoning=thought,
                    answer=answer,
                    context=context,
                )

                is_consistent = validation.get("consistent", True)
                score = validation.get("score", 0.5)

                # 如果答案不一致且启用重规划
                if (
                    not is_consistent
                    and self.enable_replanning
                    and iteration < self.max_iterations - 1
                ):
                    logger.info("答案不一致，重新规划执行路径")
                    
                    # 重新规划：基于失败原因调整策略
                    previous_reasoning = self._replan(
                        original_path=execution_path,
                        failure_reason=validation.get("reason", ""),
                        query=query,
                    )
                    
                    execution_path.append({
                        "iteration": iteration + 1,
                        "thought": thought,
                        "action": action,
                        "result": f"答案不一致，重新规划",
                        "validation": validation,
                    })
                    continue

                # 更新最佳答案
                if score > best_score:
                    best_answer = answer
                    best_score = score

                # 如果答案质量足够高，提前返回
                if score >= 0.9 and is_consistent:
                    logger.info(f"答案质量足够高 ({score:.2f})，提前返回")
                    execution_path.append({
                        "iteration": iteration + 1,
                        "thought": thought,
                        "action": action,
                        "result": answer,
                        "confidence": confidence,
                        "validation": validation,
                    })
                    return {
                        "answer": answer,
                        "confidence": confidence,
                        "score": score,
                        "sources": [doc.metadata.get("source", "unknown") for doc in context],
                        "execution_path": execution_path,
                        "iterations": iteration + 1,
                    }

                execution_path.append({
                    "iteration": iteration + 1,
                    "thought": thought,
                    "action": action,
                    "result": answer,
                    "confidence": confidence,
                    "validation": validation,
                })

            else:
                # 其他动作（检索、工具调用）
                new_docs = action_result.get("documents", [])
                context.extend(new_docs)
                context = self._deduplicate_documents(context)

                execution_path.append({
                    "iteration": iteration + 1,
                    "thought": thought,
                    "action": action,
                    "action_input": action_input,
                    "result": action_result.get("result", ""),
                    "confidence": confidence,
                })

                # 更新 previous_reasoning 用于下次迭代
                previous_reasoning = f"{thought}\n动作: {action}\n结果: {action_result.get('result', '')}"

        # 达到最大迭代次数，返回最佳答案
        final_answer = best_answer or execution_path[-1].get("result", "无法生成答案")
        
        logger.info(f"ReAct 循环完成，迭代 {len(execution_path)} 次")
        
        return {
            "answer": final_answer,
            "confidence": execution_path[-1].get("confidence", 0.5) if execution_path else 0.5,
            "score": best_score,
            "sources": [doc.metadata.get("source", "unknown") for doc in context],
            "execution_path": execution_path,
            "iterations": len(execution_path),
        }

    def _replan(
        self,
        original_path: List[Dict[str, Any]],
        failure_reason: str,
        query: str,
    ) -> str:
        """
        重新规划执行路径

        Args:
            original_path: 原始执行路径
            failure_reason: 失败原因
            query: 查询文本

        Returns:
            新的推理提示
        """
        path_summary = "\n".join([
            f"迭代 {step['iteration']}: {step.get('thought', '')[:100]}"
            for step in original_path[-3:]  # 只取最后3步
        ])

        replan_prompt = f"""之前的执行路径：
{path_summary}

失败原因：{failure_reason}

问题：{query}

请重新规划一个更好的执行路径，避免之前的错误。"""

        return replan_prompt

    def _deduplicate_documents(self, documents: List[Document]) -> List[Document]:
        """去重文档"""
        seen = set()
        unique_docs = []
        
        for doc in documents:
            doc_id = f"{doc.metadata.get('source', '')}_{doc.metadata.get('chunk_index', '')}"
            if doc_id not in seen:
                seen.add(doc_id)
                unique_docs.append(doc)
        
        return unique_docs

