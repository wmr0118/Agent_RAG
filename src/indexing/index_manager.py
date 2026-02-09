"""索引管理器"""
from typing import List, Optional, Dict, Any
from pathlib import Path
import json
from datetime import datetime
from langchain_core.documents import Document
from langchain_chroma import Chroma
from ..utils.config import get_config
from ..utils.embeddings import EmbeddingManager
from .document_loader import DocumentLoader
from .text_splitter import TextSplitter
import logging

logger = logging.getLogger(__name__)


class IndexManager:
    """索引生命周期管理器"""

    def __init__(self, config=None):
        """
        初始化索引管理器

        Args:
            config: 配置对象
        """
        if config is None:
            config = get_config()

        self.config = config
        self.vector_db_config = config.vector_db
        self.document_config = config.document

        # 初始化组件
        self.embedding_manager = EmbeddingManager(config)
        self.document_loader = DocumentLoader()
        self.text_splitter = TextSplitter(
            chunk_size=self.document_config.chunk_size,
            chunk_overlap=self.document_config.chunk_overlap,
        )

        # 索引元数据存储路径
        self.metadata_path = Path(self.vector_db_config.persist_directory) / "index_metadata.json"
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)

    def create_index(
        self,
        documents: List[Document],
        collection_name: Optional[str] = None,
        overwrite: bool = False,
    ) -> Chroma:
        """
        创建新索引

        Args:
            documents: 文档列表
            collection_name: 集合名称
            overwrite: 是否覆盖已存在的索引

        Returns:
            向量存储对象
        """
        collection_name = collection_name or self.vector_db_config.collection_name

        # 检查索引是否已存在
        if not overwrite and self.index_exists(collection_name):
            raise ValueError(f"索引已存在: {collection_name}。使用 overwrite=True 覆盖。")

        # 分割文档
        logger.info(f"开始分割 {len(documents)} 个文档")
        chunks = self.text_splitter.split_documents(documents)

        # 创建向量存储
        logger.info(f"创建向量存储: {collection_name}")
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=self.embedding_manager.embeddings,
            persist_directory=self.vector_db_config.persist_directory,
            collection_name=collection_name,
        )

        # 保存索引元数据
        self._save_index_metadata(collection_name, len(chunks), documents)

        logger.info(f"索引创建成功: {collection_name}, 包含 {len(chunks)} 个块")
        return vectorstore

    def update_index(
        self,
        documents: List[Document],
        collection_name: Optional[str] = None,
    ) -> List[str]:
        """
        更新索引（添加新文档）

        Args:
            documents: 新文档列表
            collection_name: 集合名称

        Returns:
            新添加的文档 ID 列表
        """
        collection_name = collection_name or self.vector_db_config.collection_name

        if not self.index_exists(collection_name):
            raise ValueError(f"索引不存在: {collection_name}。请先创建索引。")

        # 加载现有向量存储
        vectorstore = self.load_index(collection_name)

        # 分割新文档
        chunks = self.text_splitter.split_documents(documents)

        # 添加文档
        ids = vectorstore.add_documents(chunks)

        # 更新元数据
        metadata = self._load_index_metadata()
        if collection_name in metadata:
            metadata[collection_name]["num_chunks"] += len(chunks)
            metadata[collection_name]["updated_at"] = datetime.now().isoformat()
            self._save_index_metadata_dict(metadata)

        logger.info(f"索引更新成功: 添加了 {len(ids)} 个块")
        return ids

    def delete_index(self, collection_name: Optional[str] = None) -> bool:
        """
        删除索引

        Args:
            collection_name: 集合名称

        Returns:
            是否成功
        """
        collection_name = collection_name or self.vector_db_config.collection_name

        try:
            # 删除 Chroma 集合
            vectorstore = Chroma(
                persist_directory=self.vector_db_config.persist_directory,
                collection_name=collection_name,
                embedding_function=self.embedding_manager.embeddings,
            )
            vectorstore.delete_collection()

            # 删除元数据
            metadata = self._load_index_metadata()
            if collection_name in metadata:
                del metadata[collection_name]
                self._save_index_metadata_dict(metadata)

            logger.info(f"索引删除成功: {collection_name}")
            return True

        except Exception as e:
            logger.error(f"删除索引失败: {e}")
            return False

    def load_index(self, collection_name: Optional[str] = None) -> Chroma:
        """
        加载现有索引

        Args:
            collection_name: 集合名称

        Returns:
            向量存储对象
        """
        collection_name = collection_name or self.vector_db_config.collection_name

        if not self.index_exists(collection_name):
            raise ValueError(f"索引不存在: {collection_name}")

        vectorstore = Chroma(
            persist_directory=self.vector_db_config.persist_directory,
            collection_name=collection_name,
            embedding_function=self.embedding_manager.embeddings,
        )

        logger.info(f"索引加载成功: {collection_name}")
        return vectorstore

    def index_exists(self, collection_name: Optional[str] = None) -> bool:
        """
        检查索引是否存在

        Args:
            collection_name: 集合名称

        Returns:
            是否存在
        """
        collection_name = collection_name or self.vector_db_config.collection_name

        try:
            vectorstore = Chroma(
                persist_directory=self.vector_db_config.persist_directory,
                collection_name=collection_name,
                embedding_function=self.embedding_manager.embeddings,
            )
            # 尝试获取集合信息
            _ = vectorstore._collection.count()
            return True
        except Exception:
            return False

    def get_index_info(self, collection_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取索引信息

        Args:
            collection_name: 集合名称

        Returns:
            索引信息字典
        """
        collection_name = collection_name or self.vector_db_config.collection_name

        metadata = self._load_index_metadata()
        if collection_name not in metadata:
            return {}

        info = metadata[collection_name].copy()

        # 获取实际文档数量
        try:
            vectorstore = self.load_index(collection_name)
            info["actual_chunks"] = vectorstore._collection.count()
        except Exception:
            info["actual_chunks"] = "unknown"

        return info

    def _save_index_metadata(
        self,
        collection_name: str,
        num_chunks: int,
        original_documents: List[Document],
    ):
        """保存索引元数据"""
        metadata = self._load_index_metadata()

        metadata[collection_name] = {
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "num_chunks": num_chunks,
            "num_original_documents": len(original_documents),
            "chunk_size": self.document_config.chunk_size,
            "chunk_overlap": self.document_config.chunk_overlap,
        }

        self._save_index_metadata_dict(metadata)

    def _load_index_metadata(self) -> Dict[str, Any]:
        """加载索引元数据"""
        if not self.metadata_path.exists():
            return {}

        try:
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"加载索引元数据失败: {e}")
            return {}

    def _save_index_metadata_dict(self, metadata: Dict[str, Any]):
        """保存索引元数据字典"""
        try:
            with open(self.metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存索引元数据失败: {e}")

