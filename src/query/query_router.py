"""查询路由模块"""
from typing import Dict, Any, Optional
from .intent_classifier import QueryIntent, IntentClassifier
from .query_rewriter import QueryRewriter
from ..core.rag_chain import RAGChain
from ..utils.config import get_config
import logging

logger = logging.getLogger(__name__)


class QueryRouter:
    """查询路由器，根据意图路由到不同的 RAG 子系统"""

    def __init__(
        self,
        intent_classifier: Optional[IntentClassifier] = None,
        query_rewriter: Optional[QueryRewriter] = None,
        basic_rag: Optional[RAGChain] = None,
        config=None,
    ):
        """
        初始化查询路由器

        Args:
            intent_classifier: 意图分类器
            query_rewriter: 查询改写器
            basic_rag: 基础 RAG 链
            config: 配置对象
        """
        if config is None:
            config = get_config()

        self.config = config
        self.intent_classifier = intent_classifier or IntentClassifier(config)
        self.query_rewriter = query_rewriter or QueryRewriter(config)
        self.basic_rag = basic_rag

    def route(
        self,
        query: str,
        rag_chain: Optional[RAGChain] = None,
    ) -> Dict[str, Any]:
        """
        路由查询到相应的处理流程

        Args:
            query: 查询文本
            rag_chain: RAG 链（如果为 None，使用默认的 basic_rag）

        Returns:
            包含路由结果和处理策略的字典
        """
        # 1. 查询改写
        rewritten_query = self.query_rewriter.rewrite(query)

        # 2. 意图分类
        intent_result = self.intent_classifier.classify(rewritten_query)
        intent = intent_result["intent"]
        confidence = intent_result.get("confidence", 0.5)

        # 3. 确定处理策略
        strategy = self._determine_strategy(intent, confidence)

        # 4. 使用相应的 RAG 链
        rag_chain = rag_chain or self.basic_rag
        if rag_chain is None:
            raise ValueError("未提供 RAG 链")

        logger.info(f"查询路由: {query} -> {intent.value}, 策略: {strategy}")

        return {
            "original_query": query,
            "rewritten_query": rewritten_query,
            "intent": intent,
            "confidence": confidence,
            "strategy": strategy,
            "rag_chain": rag_chain,
        }

    def _determine_strategy(
        self, intent: QueryIntent, confidence: float
    ) -> Dict[str, Any]:
        """
        根据意图确定处理策略

        Args:
            intent: 意图类型
            confidence: 置信度

        Returns:
            策略字典
        """
        base_strategy = {
            "use_multilevel_index": True,
            "use_rerank": True,
            "top_k": self.config.retrieval.top_k,
        }

        if intent == QueryIntent.FACTUAL:
            # 简单事实查询：标准检索
            return {
                **base_strategy,
                "use_multilevel_index": True,
                "use_rerank": True,
                "top_k": self.config.retrieval.top_k,
                "use_agent": False,
            }

        elif intent == QueryIntent.COMPLEX_REASONING:
            # 复杂推理：多跳检索 + Agent
            return {
                **base_strategy,
                "use_multilevel_index": True,
                "use_rerank": True,
                "top_k": self.config.retrieval.top_k * 2,  # 更多文档
                "use_agent": True,
                "max_iterations": self.config.agent.max_iterations,
            }

        elif intent == QueryIntent.TOOL_CALL:
            # 工具调用：需要 Agent
            return {
                **base_strategy,
                "use_multilevel_index": False,
                "use_rerank": False,
                "top_k": 3,  # 少量文档用于上下文
                "use_agent": True,
                "enable_tools": True,
            }

        elif intent == QueryIntent.CONVERSATIONAL:
            # 对话：需要记忆机制
            return {
                **base_strategy,
                "use_multilevel_index": True,
                "use_rerank": True,
                "top_k": self.config.retrieval.top_k,
                "use_agent": False,
                "use_memory": True,
            }

        else:
            # 未知意图：使用默认策略
            return {
                **base_strategy,
                "use_multilevel_index": True,
                "use_rerank": True,
                "top_k": self.config.retrieval.top_k,
                "use_agent": False,
            }

