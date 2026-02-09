"""评估器"""
from typing import List, Dict, Any, Optional
import json
from pathlib import Path
from langchain_core.documents import Document
from .metrics import MetricsCalculator
from ..core.rag_chain import RAGChain
from ..agent.react_agent import ReActAgent
from ..utils.config import get_config
import logging
import time

logger = logging.getLogger(__name__)


class Evaluator:
    """综合评估器"""

    def __init__(
        self,
        rag_chain: Optional[RAGChain] = None,
        react_agent: Optional[ReActAgent] = None,
        config=None,
    ):
        """
        初始化评估器

        Args:
            rag_chain: RAG 链（用于基础 RAG 评估）
            react_agent: ReAct Agent（用于 Agent 评估）
            config: 配置对象
        """
        if config is None:
            config = get_config()

        self.config = config
        self.evaluation_config = config.evaluation
        self.metrics_calculator = MetricsCalculator()
        self.rag_chain = rag_chain
        self.react_agent = react_agent

    def evaluate(
        self,
        test_set: List[Dict[str, Any]],
        use_agent: bool = False,
    ) -> Dict[str, Any]:
        """
        执行评估

        Args:
            test_set: 测试数据集
            use_agent: 是否使用 Agent 模式

        Returns:
            评估结果字典
        """
        results = {
            "retrieval_metrics": {},
            "generation_metrics": {},
            "system_metrics": {},
            "agent_metrics": {} if use_agent else None,
        }

        all_retrieval_scores = {"recall@5": [], "recall@10": [], "precision@5": [], "mrr": []}
        all_generation_scores = {"answer_quality": [], "factual_accuracy": [], "consistency": []}
        all_latencies = []

        for i, test_case in enumerate(test_set):
            logger.info(f"评估测试用例 {i+1}/{len(test_set)}")

            query = test_case.get("question", "")
            expected_answer = test_case.get("expected_answer", "")
            relevant_docs = test_case.get("relevant_docs", [])

            # 执行查询
            start_time = time.time()
            
            if use_agent and self.react_agent:
                result = self.react_agent.react_loop(query)
                answer = result.get("answer", "")
                retrieved_docs = []  # Agent 模式下文档在内部处理
            else:
                if self.rag_chain:
                    result = self.rag_chain.query(query, return_sources=True)
                    if isinstance(result, dict):
                        answer = result.get("answer", "")
                        retrieved_docs = []  # RAG 链内部处理
                    else:
                        answer = result
                        retrieved_docs = []
                else:
                    answer = ""
                    retrieved_docs = []

            latency = time.time() - start_time
            all_latencies.append(latency)

            # 计算检索指标
            if retrieved_docs and relevant_docs:
                recall_5 = self.metrics_calculator.calculate_recall_at_k(
                    retrieved_docs, relevant_docs, k=5
                )
                recall_10 = self.metrics_calculator.calculate_recall_at_k(
                    retrieved_docs, relevant_docs, k=10
                )
                precision_5 = self.metrics_calculator.calculate_precision_at_k(
                    retrieved_docs, relevant_docs, k=5
                )
                mrr = self.metrics_calculator.calculate_mrr(retrieved_docs, relevant_docs)

                all_retrieval_scores["recall@5"].append(recall_5)
                all_retrieval_scores["recall@10"].append(recall_10)
                all_retrieval_scores["precision@5"].append(precision_5)
                all_retrieval_scores["mrr"].append(mrr)

            # 计算生成指标
            if expected_answer:
                answer_quality = self.metrics_calculator.calculate_answer_quality(
                    answer, expected_answer
                )
                factual_accuracy = self.metrics_calculator.calculate_factual_accuracy(
                    answer, retrieved_docs
                )

                all_generation_scores["answer_quality"].append(answer_quality)
                all_generation_scores["factual_accuracy"].append(factual_accuracy)

            # Agent 指标
            if use_agent and isinstance(result, dict):
                execution_path = result.get("execution_path", [])
                consistency = self.metrics_calculator.calculate_consistency(
                    [step.get("thought", "") for step in execution_path],
                    answer,
                )
                all_generation_scores["consistency"].append(consistency)

        # 计算平均指标
        results["retrieval_metrics"] = {
            metric: sum(scores) / len(scores) if scores else 0.0
            for metric, scores in all_retrieval_scores.items()
        }

        results["generation_metrics"] = {
            metric: sum(scores) / len(scores) if scores else 0.0
            for metric, scores in all_generation_scores.items()
        }

        results["system_metrics"] = {
            "avg_latency": sum(all_latencies) / len(all_latencies) if all_latencies else 0.0,
            "total_queries": len(test_set),
        }

        if use_agent:
            results["agent_metrics"] = {
                "avg_iterations": sum(
                    [
                        result.get("iterations", 0)
                        for result in [self.react_agent.react_loop(tc.get("question", "")) for tc in test_set[:10]]
                    ]
                ) / min(10, len(test_set)),
            }

        logger.info("评估完成")
        return results

    def load_test_set(self, test_set_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        加载测试数据集

        Args:
            test_set_path: 测试集路径

        Returns:
            测试数据集列表
        """
        if test_set_path is None:
            test_set_path = self.evaluation_config.test_set_path

        test_set_path = Path(test_set_path)
        if not test_set_path.exists():
            logger.warning(f"测试集文件不存在: {test_set_path}")
            return []

        try:
            with open(test_set_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # 支持多种格式
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "test_cases" in data:
                return data["test_cases"]
            else:
                logger.warning("测试集格式不支持")
                return []

        except Exception as e:
            logger.error(f"加载测试集失败: {e}")
            return []

    def compare_models(
        self,
        baseline_results: Dict[str, Any],
        current_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        对比模型结果

        Args:
            baseline_results: 基线结果
            current_results: 当前结果

        Returns:
            对比结果字典
        """
        comparison = {}

        # 检索指标对比
        if "retrieval_metrics" in baseline_results and "retrieval_metrics" in current_results:
            baseline_retrieval = baseline_results["retrieval_metrics"]
            current_retrieval = current_results["retrieval_metrics"]

            comparison["retrieval_improvement"] = {
                metric: current_retrieval.get(metric, 0.0) - baseline_retrieval.get(metric, 0.0)
                for metric in baseline_retrieval.keys()
            }

        # 生成指标对比
        if "generation_metrics" in baseline_results and "generation_metrics" in current_results:
            baseline_generation = baseline_results["generation_metrics"]
            current_generation = current_results["generation_metrics"]

            comparison["generation_improvement"] = {
                metric: current_generation.get(metric, 0.0) - baseline_generation.get(metric, 0.0)
                for metric in baseline_generation.keys()
            }

        # 系统指标对比
        if "system_metrics" in baseline_results and "system_metrics" in current_results:
            baseline_system = baseline_results["system_metrics"]
            current_system = current_results["system_metrics"]

            baseline_latency = baseline_system.get("avg_latency", 0.0)
            current_latency = current_system.get("avg_latency", 0.0)

            if baseline_latency > 0:
                comparison["latency_reduction"] = (
                    baseline_latency - current_latency
                ) / baseline_latency
            else:
                comparison["latency_reduction"] = 0.0

        return comparison

