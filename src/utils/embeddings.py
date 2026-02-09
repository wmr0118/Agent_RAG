"""Embedding 工具模块"""
from typing import List, Optional
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from .config import get_config
import logging

logger = logging.getLogger(__name__)


class EmbeddingManager:
    """Embedding 管理器"""

    def __init__(self, config=None):
        """
        初始化 Embedding 管理器

        Args:
            config: 配置对象，如果为 None 则使用默认配置
        """
        if config is None:
            config = get_config()

        embedding_config = config.embedding
        llm_config = config.llm
        provider = embedding_config.provider.lower()

        # 根据提供商创建相应的 Embedding
        # 使用 LLM 的 API key（如果 Embedding 和 LLM 使用同一个提供商）
        api_key = llm_config.api_key or None
        
        # 检查 API key 是否有效
        if not api_key or api_key.startswith("${") or api_key.startswith("your_"):
            if provider == "openai":
                raise ValueError(
                    "OpenAI API key 未设置。请设置环境变量 OPENAI_API_KEY 或创建 .env 文件。"
                )
            elif provider == "dashscope" or provider == "qwen":
                raise ValueError(
                    "DashScope API key 未设置。请设置环境变量 DASHSCOPE_API_KEY 或创建 .env 文件。\n"
                    "获取 API key: https://dashscope.console.aliyun.com/"
                )
        
        if provider == "openai":
            self.embeddings: Embeddings = OpenAIEmbeddings(
                model=embedding_config.model_name,
                api_key=api_key,
                dimensions=embedding_config.dimension,
            )
        elif provider == "dashscope" or provider == "qwen":
            # Qwen/DashScope Embedding
            self.embeddings: Embeddings = DashScopeEmbeddings(
                model=embedding_config.model_name,
                dashscope_api_key=api_key,
            )
        else:
            raise ValueError(f"不支持的 Embedding 提供商: {provider}")

        self.batch_size = embedding_config.batch_size

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        批量生成文档的 embedding

        Args:
            texts: 文本列表

        Returns:
            embedding 向量列表
        """
        try:
            embeddings = self.embeddings.embed_documents(texts)
            logger.info(f"成功生成 {len(embeddings)} 个 embedding")
            return embeddings
        except Exception as e:
            logger.error(f"生成 embedding 失败: {e}")
            raise

    def embed_query(self, text: str) -> List[float]:
        """
        生成查询的 embedding

        Args:
            text: 查询文本

        Returns:
            embedding 向量
        """
        try:
            embedding = self.embeddings.embed_query(text)
            return embedding
        except Exception as e:
            logger.error(f"生成查询 embedding 失败: {e}")
            raise

    def embed_documents_batch(
        self, documents: List[Document], batch_size: Optional[int] = None
    ) -> List[List[float]]:
        """
        批量处理文档的 embedding（分批处理）

        Args:
            documents: 文档列表
            batch_size: 批次大小

        Returns:
            embedding 向量列表
        """
        if batch_size is None:
            batch_size = self.batch_size

        texts = [doc.page_content for doc in documents]
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_embeddings = self.embed_documents(batch)
            all_embeddings.extend(batch_embeddings)
            logger.debug(f"处理批次 {i // batch_size + 1}, 进度: {min(i + batch_size, len(texts))}/{len(texts)}")

        return all_embeddings

