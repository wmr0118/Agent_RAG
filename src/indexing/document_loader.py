"""文档加载与预处理模块"""
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
    UnstructuredMarkdownLoader,
)
from langchain_core.documents import Document
import logging

logger = logging.getLogger(__name__)


class DocumentLoader:
    """文档加载器，支持多种文件格式"""

    SUPPORTED_EXTENSIONS = {
        ".pdf": PyPDFLoader,
        ".txt": TextLoader,
        ".md": TextLoader,  # 使用TextLoader代替UnstructuredMarkdownLoader，避免NLTK依赖
        ".docx": Docx2txtLoader,
    }

    def __init__(self, base_path: Optional[str] = None):
        """
        初始化文档加载器

        Args:
            base_path: 文档基础路径
        """
        self.base_path = Path(base_path) if base_path else Path.cwd()

    def load_file(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        加载单个文件

        Args:
            file_path: 文件路径
            metadata: 额外的元数据

        Returns:
            文档列表
        """
        file_path = Path(file_path)
        if not file_path.is_absolute():
            file_path = self.base_path / file_path

        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        extension = file_path.suffix.lower()
        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件格式: {extension}")

        loader_class = self.SUPPORTED_EXTENSIONS[extension]
        loader = loader_class(str(file_path))

        try:
            documents = loader.load()
            
            # 添加元数据
            base_metadata = {
                "source": str(file_path),
                "file_name": file_path.name,
                "file_type": extension,
            }
            if metadata:
                base_metadata.update(metadata)

            for doc in documents:
                doc.metadata.update(base_metadata)

            logger.info(f"成功加载文件: {file_path}, 文档数: {len(documents)}")
            return documents

        except Exception as e:
            logger.error(f"加载文件失败: {file_path}, 错误: {e}")
            raise

    def load_directory(
        self,
        directory_path: str,
        recursive: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """
        加载目录中的所有支持的文件

        Args:
            directory_path: 目录路径
            recursive: 是否递归加载子目录
            metadata: 额外的元数据

        Returns:
            文档列表
        """
        directory_path = Path(directory_path)
        if not directory_path.is_absolute():
            directory_path = self.base_path / directory_path

        if not directory_path.exists():
            raise FileNotFoundError(f"目录不存在: {directory_path}")

        all_documents = []
        pattern = "**/*" if recursive else "*"

        for ext in self.SUPPORTED_EXTENSIONS.keys():
            for file_path in directory_path.glob(f"{pattern}{ext}"):
                try:
                    docs = self.load_file(file_path, metadata)
                    all_documents.extend(docs)
                except Exception as e:
                    logger.warning(f"跳过文件 {file_path}: {e}")

        logger.info(f"从目录 {directory_path} 加载了 {len(all_documents)} 个文档")
        return all_documents

    def load_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> Document:
        """
        从文本字符串加载文档

        Args:
            text: 文本内容
            metadata: 元数据

        Returns:
            文档对象
        """
        base_metadata = metadata or {}
        return Document(page_content=text, metadata=base_metadata)

    def clean_document(self, document: Document) -> Document:
        """
        清理文档内容（去除噪声、模板文本等）

        Args:
            document: 原始文档

        Returns:
            清理后的文档
        """
        text = document.page_content

        # 去除多余的空白字符
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join([line for line in lines if line])

        # 去除低信息密度文本（如页眉页脚）
        # 这里可以添加更多清理规则

        return Document(page_content=text, metadata=document.metadata)

    def clean_documents(self, documents: List[Document]) -> List[Document]:
        """
        批量清理文档

        Args:
            documents: 文档列表

        Returns:
            清理后的文档列表
        """
        return [self.clean_document(doc) for doc in documents]

