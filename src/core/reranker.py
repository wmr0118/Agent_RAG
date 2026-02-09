"""重排序模块"""
from typing import List, Tuple
from langchain_core.documents import Document
from ..utils.config import get_config
from ..utils.llm_factory import LLMFactory
import logging

logger = logging.getLogger(__name__)


class Reranker:
    """重排序器，使用LLM对检索结果进行重排序"""

    def __init__(self, config=None):
        """
        初始化重排序器

        Args:
            config: 配置对象
        """
        if config is None:
            config = get_config()

        self.config = config
        
        # 使用较小的模型进行重排序以节省成本
        self.llm = LLMFactory.create_llm(
            config=config,
            temperature=0.1,  # 低温度保证稳定性
        )

    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_n: int = 5,
    ) -> List[Document]:
        """
        对文档进行重排序

        Args:
            query: 查询文本
            documents: 文档列表
            top_n: 返回前N个文档

        Returns:
            重排序后的文档列表
        """
        if not documents:
            return []

        if len(documents) <= top_n:
            # 如果文档数量少于top_n，直接返回
            return documents

        try:
            # 构建重排序prompt
            prompt = self._build_rerank_prompt(query, documents)
            
            # 调用LLM进行重排序
            response = self.llm.invoke(prompt)
            result_text = response.content if hasattr(response, "content") else str(response)
            
            # 解析重排序结果
            reranked_indices = self._parse_rerank_result(result_text, len(documents))
            
            # 根据索引重排序文档
            reranked_docs = [documents[i] for i in reranked_indices[:top_n] if i < len(documents)]
            
            logger.info(f"重排序完成: {len(documents)} -> {len(reranked_docs)} 个文档")
            return reranked_docs

        except Exception as e:
            logger.warning(f"重排序失败，使用原始顺序: {e}")
            return documents[:top_n]

    def _build_rerank_prompt(self, query: str, documents: List[Document]) -> str:
        """构建重排序prompt"""
        doc_texts = []
        for i, doc in enumerate(documents):
            # 截取文档前500字符（避免prompt过长）
            content = doc.page_content[:500]
            doc_texts.append(f"[文档{i}]\n{content}")

        prompt = f"""请根据以下查询，对文档进行相关性排序，返回最相关的文档索引（从0开始）。

查询：{query}

文档列表：
{chr(10).join(doc_texts)}

请按照相关性从高到低排序，返回文档索引列表（用逗号分隔）。
例如：2,0,1,3,4

只返回索引列表，不要其他内容："""

        return prompt

    def _parse_rerank_result(self, result_text: str, max_index: int) -> List[int]:
        """解析重排序结果"""
        try:
            # 提取数字
            import re
            indices = re.findall(r'\d+', result_text)
            indices = [int(i) for i in indices if int(i) < max_index]
            
            # 去重并保持顺序
            seen = set()
            unique_indices = []
            for idx in indices:
                if idx not in seen:
                    seen.add(idx)
                    unique_indices.append(idx)
            
            # 如果解析失败，返回原始顺序
            if not unique_indices:
                return list(range(max_index))
            
            # 补充缺失的索引
            for i in range(max_index):
                if i not in unique_indices:
                    unique_indices.append(i)
            
            return unique_indices[:max_index]

        except Exception as e:
            logger.warning(f"解析重排序结果失败: {e}")
            return list(range(max_index))

    def rerank_with_scores(
        self,
        query: str,
        documents_with_scores: List[Tuple[Document, float]],
        top_n: int = 5,
    ) -> List[Tuple[Document, float]]:
        """
        对带分数的文档进行重排序

        Args:
            query: 查询文本
            documents_with_scores: (文档, 分数) 元组列表
            top_n: 返回前N个文档

        Returns:
            重排序后的(文档, 分数)元组列表
        """
        documents = [doc for doc, score in documents_with_scores]
        reranked_docs = self.rerank(query, documents, top_n)
        
        # 重新构建带分数的结果（使用原始分数或重新计算）
        reranked_with_scores = []
        for doc in reranked_docs:
            # 找到原始分数
            original_score = next(
                (score for d, score in documents_with_scores if d.page_content == doc.page_content),
                0.0
            )
            reranked_with_scores.append((doc, original_score))
        
        return reranked_with_scores

