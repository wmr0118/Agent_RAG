"""多级索引实现"""
from typing import List, Optional, Dict, Any, Set
from langchain_core.documents import Document
from langchain_chroma import Chroma
from ..utils.config import get_config
from ..utils.embeddings import EmbeddingManager
from ..utils.llm_factory import LLMFactory
from .text_splitter import TextSplitter
import logging

logger = logging.getLogger(__name__)


class MultilevelIndex:
    """多级索引结构"""

    def __init__(
        self,
        level1_vectorstore: Optional[Chroma] = None,
        level2_vectorstore: Optional[Chroma] = None,
        level3_vectorstore: Optional[Chroma] = None,
        config=None,
    ):
        """
        初始化多级索引

        Args:
            level1_vectorstore: 一级索引（主题/摘要级别）
            level2_vectorstore: 二级索引（文档块级别）
            level3_vectorstore: 三级索引（句子级别）
            config: 配置对象
        """
        if config is None:
            config = get_config()

        self.config = config
        self.multilevel_config = config.multilevel_index
        self.embedding_manager = EmbeddingManager(config)

        # 初始化各级索引
        self.level1_store = level1_vectorstore
        self.level2_store = level2_vectorstore
        self.level3_store = level3_vectorstore

        # 文本分割器（用于三级索引）
        self.sentence_splitter = TextSplitter(chunk_size=200, chunk_overlap=50)

    def build_from_documents(
        self,
        documents: List[Document],
        collection_prefix: str = "multilevel",
    ):
        """
        从文档构建多级索引

        Args:
            documents: 文档列表
            collection_prefix: 集合名称前缀
        """
        logger.info(f"开始构建多级索引，文档数: {len(documents)}")

        # 构建一级索引（主题/摘要级别）
        if self.multilevel_config.level1.get("enabled", True):
            logger.info("构建一级索引（主题/摘要级别）")
            level1_docs = self._create_level1_documents(documents)
            self.level1_store = Chroma.from_documents(
                documents=level1_docs,
                embedding=self.embedding_manager.embeddings,
                persist_directory=self.config.vector_db.persist_directory,
                collection_name=f"{collection_prefix}_level1",
            )

        # 构建二级索引（文档块级别）
        if self.multilevel_config.level2.get("enabled", True):
            logger.info("构建二级索引（文档块级别）")
            text_splitter = TextSplitter(
                chunk_size=self.config.document.chunk_size,
                chunk_overlap=self.config.document.chunk_overlap,
            )
            level2_docs = text_splitter.split_documents(documents)
            self.level2_store = Chroma.from_documents(
                documents=level2_docs,
                embedding=self.embedding_manager.embeddings,
                persist_directory=self.config.vector_db.persist_directory,
                collection_name=f"{collection_prefix}_level2",
            )

        # 构建三级索引（句子级别）
        if self.multilevel_config.level3.get("enabled", True):
            logger.info("构建三级索引（句子级别）")
            level3_docs = []
            for doc in documents:
                sentence_chunks = self.sentence_splitter.create_sentence_level_chunks(doc)
                level3_docs.extend(sentence_chunks)
            self.level3_store = Chroma.from_documents(
                documents=level3_docs,
                embedding=self.embedding_manager.embeddings,
                persist_directory=self.config.vector_db.persist_directory,
                collection_name=f"{collection_prefix}_level3",
            )

        logger.info("多级索引构建完成")

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
    ) -> List[Document]:
        """
        多级检索策略

        Args:
            query: 查询文本
            top_k: 返回的文档数量

        Returns:
            检索到的文档列表
        """
        if top_k is None:
            top_k = self.config.retrieval.top_k

        all_documents = []
        seen_ids: Set[str] = set()

        # 一级检索：粗粒度主题匹配
        if self.level1_store and self.multilevel_config.level1.get("enabled", True):
            level1_k = self.multilevel_config.level1.get("top_k", 10)
            level1_docs = self.level1_store.similarity_search(query, k=level1_k)
            
            # 提取一级检索到的文档来源
            level1_sources = {doc.metadata.get("source") for doc in level1_docs if doc.metadata.get("source")}
            
            logger.info(f"一级检索: {len(level1_docs)} 个文档")

        # 二级检索：标准块级别检索（可选：限制在一级检索的文档范围内）
        if self.level2_store and self.multilevel_config.level2.get("enabled", True):
            level2_k = self.multilevel_config.level2.get("top_k", 5)
            
            # 如果有一级检索结果，可以用于过滤
            level2_docs = self.level2_store.similarity_search(query, k=level2_k)
            
            # 去重并添加
            for doc in level2_docs:
                doc_id = self._get_doc_id(doc)
                if doc_id not in seen_ids:
                    all_documents.append(doc)
                    seen_ids.add(doc_id)
            
            logger.info(f"二级检索: {len(level2_docs)} 个文档")

        # 三级检索：句子级别精确匹配（补充）
        if self.level3_store and self.multilevel_config.level3.get("enabled", True):
            level3_k = self.multilevel_config.level3.get("top_k", 3)
            level3_docs = self.level3_store.similarity_search(query, k=level3_k)
            
            # 去重并添加
            for doc in level3_docs:
                doc_id = self._get_doc_id(doc)
                if doc_id not in seen_ids:
                    all_documents.append(doc)
                    seen_ids.add(doc_id)
            
            logger.info(f"三级检索: {len(level3_docs)} 个文档")

        # 限制返回数量
        final_docs = all_documents[:top_k]
        logger.info(f"多级检索完成，返回 {len(final_docs)} 个文档")
        
        return final_docs

    def _create_level1_documents(self, documents: List[Document]) -> List[Document]:
        """
        创建一级索引文档（主题/摘要级别）

        Args:
            documents: 原始文档列表

        Returns:
            一级索引文档列表
        """
        level1_docs = []

        # 使用 LLM 生成摘要
        llm = LLMFactory.create_llm(
            config=self.config,
            temperature=0.3,
        )

        for doc in documents:
            # 如果文档有标题，使用标题
            title = doc.metadata.get("title") or doc.metadata.get("file_name", "")

            # 生成摘要（如果文档较长）
            if len(doc.page_content) > 500:
                summary_prompt = f"""请为以下文档生成一个简洁的主题摘要（50-100字）：

{document.page_content[:2000]}

摘要："""
                try:
                    response = llm.invoke(summary_prompt)
                    summary = response.content if hasattr(response, "content") else str(response)
                except Exception as e:
                    logger.warning(f"生成摘要失败: {e}")
                    summary = doc.page_content[:200]  # 使用前200字符作为摘要
            else:
                summary = doc.page_content

            # 创建一级索引文档
            level1_doc = Document(
                page_content=f"主题: {title}\n摘要: {summary}",
                metadata={
                    **doc.metadata,
                    "level": 1,
                    "index_type": "summary",
                },
            )
            level1_docs.append(level1_doc)

        return level1_docs

    def _get_doc_id(self, doc: Document) -> str:
        """获取文档的唯一标识"""
        source = doc.metadata.get("source", "")
        chunk_index = doc.metadata.get("chunk_index", "")
        return f"{source}_{chunk_index}"

