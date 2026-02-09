"""基础向量检索器"""
from typing import List, Optional, Dict, Any
from langchain_chroma import Chroma
from langchain_core.documents import Document
from .reranker import Reranker
from ..utils.config import get_config
from ..utils.embeddings import EmbeddingManager
import logging

logger = logging.getLogger(__name__)


class BaseRetriever:
    """基础向量检索器"""

    def __init__(
        self,
        vectorstore: Optional[Chroma] = None,
        config=None,
        use_mmr: bool = True,
        use_rerank: bool = False,
    ):
        """
        初始化检索器

        Args:
            vectorstore: 向量存储对象，如果为 None 则创建新的
            config: 配置对象
            use_mmr: 是否使用 MMR（最大边际相关性）检索
            use_rerank: 是否使用重排序
        """
        if config is None:
            config = get_config()

        self.config = config
        self.retrieval_config = config.retrieval
        self.use_mmr = use_mmr if use_mmr else self.retrieval_config.use_mmr
        self.use_rerank = use_rerank if use_rerank else self.retrieval_config.rerank

        # 初始化 embedding
        self.embedding_manager = EmbeddingManager(config)

        # 初始化向量存储
        if vectorstore is None:
            self.vectorstore = self._create_vectorstore()
        else:
            self.vectorstore = vectorstore

        # 初始化检索器
        self.retriever = self._create_retriever()

        # 初始化重排序器（如果启用）
        self.reranker = None
        if self.use_rerank:
            try:
                self.reranker = Reranker(config=config)
                logger.info("重排序器初始化成功")
            except Exception as e:
                logger.warning(f"重排序器初始化失败: {e}，将不使用重排序")
                self.use_rerank = False

    def _create_vectorstore(self) -> Chroma:
        """创建向量存储"""
        vector_db_config = self.config.vector_db
        embedding = self.embedding_manager.embeddings

        vectorstore = Chroma(
            persist_directory=vector_db_config.persist_directory,
            collection_name=vector_db_config.collection_name,
            embedding_function=embedding,
        )

        logger.info(f"向量存储已创建: {vector_db_config.collection_name}")
        return vectorstore

    def _create_retriever(self):
        """创建检索器"""
        if self.use_mmr:
            retriever = self.vectorstore.as_retriever(
                search_type="mmr",
                search_kwargs={
                    "k": self.retrieval_config.top_k,
                    "fetch_k": self.retrieval_config.top_k * 2,
                    "lambda_mult": self.retrieval_config.mmr_diversity,
                },
            )
        else:
            retriever = self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={
                    "k": self.retrieval_config.top_k,
                    "score_threshold": self.retrieval_config.similarity_threshold,
                },
            )

        return retriever


    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """
        检索相关文档

        Args:
            query: 查询文本
            top_k: 返回的文档数量
            filter: 元数据过滤条件

        Returns:
            相关文档列表
        """
        if top_k is None:
            top_k = self.retrieval_config.top_k

        # 更新检索器的 top_k
        if hasattr(self.retriever, "search_kwargs"):
            self.retriever.search_kwargs["k"] = top_k

        try:
            if filter:
                # 如果使用过滤，直接使用向量存储的相似度搜索
                docs = self.vectorstore.similarity_search_with_score(
                    query=query,
                    k=top_k,
                    filter=filter,
                )
                # 处理带分数的结果
                documents = [doc for doc, score in docs]
            else:
                # LangChain v1.2 中使用 invoke 方法
                try:
                    documents = self.retriever.invoke(query)
                except AttributeError:
                    # 如果 invoke 不存在，尝试使用 _get_relevant_documents
                    try:
                        documents = self.retriever._get_relevant_documents(query)
                    except AttributeError:
                        # 最后尝试使用 get_relevant_documents（向后兼容）
                        documents = self.retriever.get_relevant_documents(query)

            logger.info(f"检索到 {len(documents)} 个相关文档")
            
            # 如果启用重排序，对结果进行重排序
            if self.use_rerank and self.reranker and len(documents) > 1:
                rerank_top_n = getattr(self.retrieval_config, "rerank_top_n", len(documents))
                documents = self.reranker.rerank(query, documents, top_n=rerank_top_n)
                logger.info(f"重排序完成，返回前 {len(documents)} 个文档")
            
            return documents

        except Exception as e:
            logger.error(f"检索失败: {e}")
            raise

    def retrieve_with_scores(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[tuple[Document, float]]:
        """
        检索相关文档（带相似度分数）

        Args:
            query: 查询文本
            top_k: 返回的文档数量
            filter: 元数据过滤条件

        Returns:
            (文档, 分数) 元组列表
        """
        if top_k is None:
            top_k = self.retrieval_config.top_k

        try:
            docs_with_scores = self.vectorstore.similarity_search_with_score(
                query=query,
                k=top_k,
                filter=filter,
            )

            logger.info(f"检索到 {len(docs_with_scores)} 个相关文档（带分数）")
            return docs_with_scores

        except Exception as e:
            logger.error(f"检索失败: {e}")
            raise

    def add_documents(self, documents: List[Document]) -> List[str]:
        """
        添加文档到向量存储

        Args:
            documents: 文档列表

        Returns:
            文档 ID 列表
        """
        try:
            ids = self.vectorstore.add_documents(documents)
            logger.info(f"成功添加 {len(ids)} 个文档到向量存储")
            return ids
        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            raise

    def delete_documents(self, ids: List[str]) -> bool:
        """
        从向量存储删除文档

        Args:
            ids: 文档 ID 列表

        Returns:
            是否成功
        """
        try:
            self.vectorstore.delete(ids=ids)
            logger.info(f"成功删除 {len(ids)} 个文档")
            return True
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False

    def expand_retrieval(
        self,
        query: str,
        original_top_k: int,
        expansion_factor: int = 4,
    ) -> List[Document]:
        """
        扩大检索范围（用于二次检索）

        Args:
            query: 查询文本
            original_top_k: 原始 top_k
            expansion_factor: 扩展因子

        Returns:
            扩展后的文档列表
        """
        expanded_top_k = original_top_k * expansion_factor
        return self.retrieve(query, top_k=expanded_top_k)

