"""文本分割模块"""
from typing import List, Optional
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    CharacterTextSplitter,
)
from langchain_core.documents import Document
import logging

logger = logging.getLogger(__name__)


class TextSplitter:
    """文本分割器，支持多种分割策略"""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separator: str = "\n\n",
        keep_separator: bool = True,
    ):
        """
        初始化文本分割器

        Args:
            chunk_size: 块大小（字符数）
            chunk_overlap: 块重叠大小
            separator: 分隔符
            keep_separator: 是否保留分隔符
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator
        self.keep_separator = keep_separator

        # 使用递归字符分割器（推荐）
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", " ", ""],
            length_function=len,
        )

    def split_document(self, document: Document) -> List[Document]:
        """
        分割单个文档

        Args:
            document: 文档对象

        Returns:
            分割后的文档块列表
        """
        texts = self.splitter.split_text(document.page_content)
        
        chunks = []
        for i, text in enumerate(texts):
            chunk = Document(
                page_content=text,
                metadata={
                    **document.metadata,
                    "chunk_index": i,
                    "total_chunks": len(texts),
                },
            )
            chunks.append(chunk)

        logger.debug(f"文档分割完成: {len(chunks)} 个块")
        return chunks

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        批量分割文档

        Args:
            documents: 文档列表

        Returns:
            分割后的文档块列表
        """
        all_chunks = []
        for doc in documents:
            chunks = self.split_document(doc)
            all_chunks.extend(chunks)

        logger.info(f"总共分割为 {len(all_chunks)} 个块")
        return all_chunks

    def split_text(self, text: str, metadata: Optional[dict] = None) -> List[Document]:
        """
        分割文本字符串

        Args:
            text: 文本内容
            metadata: 元数据

        Returns:
            分割后的文档块列表
        """
        document = Document(
            page_content=text,
            metadata=metadata or {},
        )
        return self.split_document(document)

    def create_sentence_level_chunks(self, document: Document) -> List[Document]:
        """
        创建句子级别的块（用于三级索引）

        Args:
            document: 文档对象

        Returns:
            句子级别的文档块列表
        """
        # 使用更小的块大小进行句子级别分割
        sentence_splitter = RecursiveCharacterTextSplitter(
            chunk_size=200,
            chunk_overlap=50,
            separators=["。", "！", "？", "\n", ".", "!", "?", " "],
            length_function=len,
        )

        texts = sentence_splitter.split_text(document.page_content)
        chunks = []
        for i, text in enumerate(texts):
            chunk = Document(
                page_content=text.strip(),
                metadata={
                    **document.metadata,
                    "chunk_index": i,
                    "chunk_type": "sentence",
                },
            )
            chunks.append(chunk)

        return chunks

