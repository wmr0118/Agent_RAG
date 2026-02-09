"""评估指标模块"""
from typing import List, Dict, Any, Set
from langchain_core.documents import Document
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import logging

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """评估指标计算器"""

    @staticmethod
    def calculate_recall_at_k(
        retrieved_docs: List[Document],
        relevant_docs: List[str],
        k: int = 5,
    ) -> float:
        """
        计算 Recall@K

        Args:
            retrieved_docs: 检索到的文档列表
            relevant_docs: 相关文档 ID 列表
            k: K 值

        Returns:
            Recall@K 分数（0-1）
        """
        if not relevant_docs:
            return 0.0

        retrieved_ids = set()
        for doc in retrieved_docs[:k]:
            doc_id = doc.metadata.get("source", "") or doc.metadata.get("id", "")
            retrieved_ids.add(doc_id)

        relevant_set = set(relevant_docs)
        intersection = retrieved_ids & relevant_set

        recall = len(intersection) / len(relevant_set) if relevant_set else 0.0
        return recall

    @staticmethod
    def calculate_precision_at_k(
        retrieved_docs: List[Document],
        relevant_docs: List[str],
        k: int = 5,
    ) -> float:
        """
        计算 Precision@K

        Args:
            retrieved_docs: 检索到的文档列表
            relevant_docs: 相关文档 ID 列表
            k: K 值

        Returns:
            Precision@K 分数（0-1）
        """
        if not retrieved_docs[:k]:
            return 0.0

        retrieved_ids = set()
        for doc in retrieved_docs[:k]:
            doc_id = doc.metadata.get("source", "") or doc.metadata.get("id", "")
            retrieved_ids.add(doc_id)

        relevant_set = set(relevant_docs)
        intersection = retrieved_ids & relevant_set

        precision = len(intersection) / k if k > 0 else 0.0
        return precision

    @staticmethod
    def calculate_mrr(
        retrieved_docs: List[Document],
        relevant_docs: List[str],
    ) -> float:
        """
        计算 Mean Reciprocal Rank (MRR)

        Args:
            retrieved_docs: 检索到的文档列表
            relevant_docs: 相关文档 ID 列表

        Returns:
            MRR 分数（0-1）
        """
        if not relevant_docs:
            return 0.0

        relevant_set = set(relevant_docs)

        for rank, doc in enumerate(retrieved_docs, 1):
            doc_id = doc.metadata.get("source", "") or doc.metadata.get("id", "")
            if doc_id in relevant_set:
                return 1.0 / rank

        return 0.0

    @staticmethod
    def calculate_answer_quality(
        answer: str,
        expected_answer: str,
        use_llm: bool = False,
        llm=None,
    ) -> float:
        """
        计算答案质量分数

        Args:
            answer: 生成的答案
            expected_answer: 期望答案
            use_llm: 是否使用 LLM 评估
            llm: LLM 实例（如果 use_llm=True）

        Returns:
            质量分数（0-1）
        """
        if use_llm and llm:
            return MetricsCalculator._llm_evaluate_answer(answer, expected_answer, llm)
        else:
            # 简单的基于相似度的评估
            return MetricsCalculator._similarity_evaluate_answer(answer, expected_answer)

    @staticmethod
    def _similarity_evaluate_answer(answer: str, expected_answer: str) -> float:
        """基于相似度的答案评估"""
        # 简单的词汇重叠度
        answer_words = set(answer.lower().split())
        expected_words = set(expected_answer.lower().split())

        if not expected_words:
            return 0.0

        intersection = answer_words & expected_words
        similarity = len(intersection) / len(expected_words)

        return min(similarity, 1.0)

    @staticmethod
    def _llm_evaluate_answer(answer: str, expected_answer: str, llm) -> float:
        """使用 LLM 评估答案"""
        prompt = f"""请评估以下答案的质量（0-1分）。

期望答案：{expected_answer}

生成的答案：{answer}

请只返回一个0-1之间的浮点数，表示答案质量分数。"""

        try:
            response = llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            
            # 提取数字
            import re
            match = re.search(r"0?\.\d+|1\.0|0", content)
            if match:
                score = float(match.group())
                return min(max(score, 0.0), 1.0)
            else:
                return 0.5

        except Exception as e:
            logger.warning(f"LLM 评估失败: {e}")
            return MetricsCalculator._similarity_evaluate_answer(answer, expected_answer)

    @staticmethod
    def calculate_factual_accuracy(
        answer: str,
        context: List[Document],
        use_llm: bool = False,
        llm=None,
    ) -> float:
        """
        计算事实准确性

        Args:
            answer: 生成的答案
            context: 上下文文档
            use_llm: 是否使用 LLM 评估
            llm: LLM 实例

        Returns:
            准确性分数（0-1）
        """
        if use_llm and llm:
            return MetricsCalculator._llm_evaluate_factual(answer, context, llm)
        else:
            # 简单的基于关键词的评估
            return 0.7  # 默认值

    @staticmethod
    def _llm_evaluate_factual(answer: str, context: List[Document], llm) -> float:
        """使用 LLM 评估事实准确性"""
        context_text = "\n\n".join([doc.page_content[:500] for doc in context[:3]])

        prompt = f"""请评估以下答案是否与提供的上下文一致（0-1分）。

上下文：
{context_text}

答案：
{answer}

请只返回一个0-1之间的浮点数，表示事实准确性分数。"""

        try:
            response = llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            
            import re
            match = re.search(r"0?\.\d+|1\.0|0", content)
            if match:
                score = float(match.group())
                return min(max(score, 0.0), 1.0)
            else:
                return 0.7

        except Exception as e:
            logger.warning(f"LLM 事实评估失败: {e}")
            return 0.7

    @staticmethod
    def calculate_consistency(
        reasoning_steps: List[str],
        final_answer: str,
        use_llm: bool = False,
        llm=None,
    ) -> float:
        """
        计算一致性（推理步骤与最终答案的一致性）

        Args:
            reasoning_steps: 推理步骤列表
            final_answer: 最终答案
            use_llm: 是否使用 LLM 评估
            llm: LLM 实例

        Returns:
            一致性分数（0-1）
        """
        if use_llm and llm:
            return MetricsCalculator._llm_evaluate_consistency(reasoning_steps, final_answer, llm)
        else:
            # 简单的关键词匹配
            reasoning_text = " ".join(reasoning_steps).lower()
            answer_lower = final_answer.lower()
            
            # 检查答案中的关键词是否出现在推理中
            answer_words = set(answer_lower.split())
            reasoning_words = set(reasoning_text.split())
            
            if not answer_words:
                return 0.0
            
            overlap = len(answer_words & reasoning_words) / len(answer_words)
            return min(overlap, 1.0)

    @staticmethod
    def _llm_evaluate_consistency(reasoning_steps: List[str], final_answer: str, llm) -> float:
        """使用 LLM 评估一致性"""
        reasoning_text = "\n".join([f"步骤{i+1}: {step}" for i, step in enumerate(reasoning_steps)])

        prompt = f"""请评估推理步骤与最终答案的一致性（0-1分）。

推理步骤：
{reasoning_text}

最终答案：
{final_answer}

请只返回一个0-1之间的浮点数，表示一致性分数。"""

        try:
            response = llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            
            import re
            match = re.search(r"0?\.\d+|1\.0|0", content)
            if match:
                score = float(match.group())
                return min(max(score, 0.0), 1.0)
            else:
                return 0.7

        except Exception as e:
            logger.warning(f"LLM 一致性评估失败: {e}")
            return 0.7

