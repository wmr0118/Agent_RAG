"""查询改写模块"""
from typing import List, Optional
from ..utils.config import get_config
from ..utils.llm_factory import LLMFactory
import logging

logger = logging.getLogger(__name__)


class QueryRewriter:
    """查询改写器，支持查询扩展和简化"""

    def __init__(self, config=None):
        """
        初始化查询改写器

        Args:
            config: 配置对象
        """
        if config is None:
            config = get_config()

        self.config = config
        query_config = config.query
        llm_config = config.llm

        # 使用较小的模型进行改写以节省成本
        # 如果配置了 rewrite_model，使用它；否则使用默认模型
        rewrite_model = query_config.rewrite_model if hasattr(query_config, 'rewrite_model') else llm_config.model_name
        self.llm = LLMFactory.create_llm(
            config=config,
            model_name=rewrite_model,
            temperature=0.3,
        )

    def rewrite(self, query: str, mode: str = "auto") -> str:
        """
        改写查询

        Args:
            query: 原始查询
            mode: 改写模式 ("auto", "expand", "simplify")

        Returns:
            改写后的查询
        """
        if not self.config.query.enable_rewrite:
            return query

        if mode == "auto":
            # 自动判断：简单查询扩展，复杂查询简化
            mode = self._detect_query_complexity(query)

        if mode == "expand":
            return self.expand_query(query)
        elif mode == "simplify":
            return self.simplify_query(query)
        else:
            return query

    def expand_query(self, query: str) -> str:
        """
        扩展查询（添加同义词、关联词）

        Args:
            query: 原始查询

        Returns:
            扩展后的查询
        """
        prompt = f"""请将以下查询扩展为更全面的搜索查询，添加相关的同义词、关联词和上下文信息。
保持原查询的核心意图不变。

原始查询：{query}

扩展后的查询："""

        try:
            response = self.llm.invoke(prompt)
            expanded = response.content if hasattr(response, "content") else str(response)
            expanded = expanded.strip().strip('"').strip("'")
            
            logger.info(f"查询扩展: {query} -> {expanded}")
            return expanded

        except Exception as e:
            logger.warning(f"查询扩展失败，使用原查询: {e}")
            return query

    def simplify_query(self, query: str) -> str:
        """
        简化查询（提取核心意图）

        Args:
            query: 原始查询

        Returns:
            简化后的查询
        """
        prompt = f"""请将以下复杂查询简化为核心搜索意图，去除冗余信息和修饰词。

原始查询：{query}

简化后的查询："""

        try:
            response = self.llm.invoke(prompt)
            simplified = response.content if hasattr(response, "content") else str(response)
            simplified = simplified.strip().strip('"').strip("'")
            
            logger.info(f"查询简化: {query} -> {simplified}")
            return simplified

        except Exception as e:
            logger.warning(f"查询简化失败，使用原查询: {e}")
            return query

    def generate_alternative_queries(self, query: str, num: int = 3) -> List[str]:
        """
        生成多个替代查询

        Args:
            query: 原始查询
            num: 生成数量

        Returns:
            替代查询列表
        """
        prompt = f"""请为以下查询生成 {num} 个不同角度的替代查询，每个查询应该从不同角度表达相同或相关的意图。

原始查询：{query}

请生成 {num} 个替代查询，每行一个："""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            
            # 解析多行结果
            alternatives = [
                line.strip().strip('"').strip("'")
                for line in content.split("\n")
                if line.strip() and not line.strip().startswith("#")
            ][:num]

            logger.info(f"生成了 {len(alternatives)} 个替代查询")
            return alternatives

        except Exception as e:
            logger.warning(f"生成替代查询失败: {e}")
            return [query]

    def _detect_query_complexity(self, query: str) -> str:
        """
        检测查询复杂度

        Args:
            query: 查询文本

        Returns:
            "expand" 或 "simplify"
        """
        # 简单启发式规则
        word_count = len(query.split())
        
        # 如果查询很短（少于5个词），可能需要扩展
        if word_count < 5:
            return "expand"
        
        # 如果查询很长（超过20个词），可能需要简化
        if word_count > 20:
            return "simplify"
        
        # 默认不改变
        return "auto"

