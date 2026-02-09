"""记忆检索模块"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from langchain_core.documents import Document
from .memory_store import MemoryStore
from ..utils.config import get_config
import logging

logger = logging.getLogger(__name__)


class MemoryRetriever:
    """记忆检索器，检索用户相关历史"""

    def __init__(self, memory_store: Optional[MemoryStore] = None, config=None):
        """
        初始化记忆检索器

        Args:
            memory_store: 记忆存储对象
            config: 配置对象
        """
        if config is None:
            config = get_config()

        self.config = config
        self.memory_config = config.memory
        self.memory_store = memory_store or MemoryStore(config)

    def retrieve(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
    ) -> List[Document]:
        """
        检索相关历史记忆

        Args:
            query: 查询文本
            user_id: 用户 ID
            top_k: 返回的记忆数量

        Returns:
            相关记忆文档列表
        """
        if not self.memory_config.enabled:
            return []

        try:
            # 检索记忆
            memories = self.memory_store.vectorstore.similarity_search(
                query=query,
                k=top_k,
                filter={"user_id": user_id},
            )

            # 应用时间衰减权重
            weighted_memories = self._apply_time_decay(memories)

            logger.info(f"检索到 {len(weighted_memories)} 条相关记忆")
            return weighted_memories

        except Exception as e:
            logger.warning(f"记忆检索失败: {e}")
            return []

    def retrieve_as_context(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
    ) -> str:
        """
        检索记忆并格式化为上下文字符串

        Args:
            query: 查询文本
            user_id: 用户 ID
            top_k: 返回的记忆数量

        Returns:
            格式化的上下文字符串
        """
        memories = self.retrieve(query, user_id, top_k)

        if not memories:
            return ""

        # 格式化记忆为上下文
        context_parts = ["相关历史对话："]
        for i, mem in enumerate(memories, 1):
            query_text = mem.metadata.get("query", "")
            answer_text = mem.metadata.get("answer", "")
            timestamp = mem.metadata.get("timestamp", "")
            
            context_parts.append(
                f"{i}. 问题: {query_text}\n   回答: {answer_text}\n   时间: {timestamp}"
            )

        return "\n".join(context_parts)

    def _apply_time_decay(self, memories: List[Document]) -> List[Document]:
        """
        应用时间衰减权重

        Args:
            memories: 记忆文档列表

        Returns:
            加权后的记忆列表（按相关性排序）
        """
        now = datetime.now()
        expiry_days = self.memory_config.memory_expiry_days

        weighted_memories = []
        for mem in memories:
            timestamp_str = mem.metadata.get("timestamp", "")
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
                age_days = (now - timestamp).days

                # 计算时间衰减权重（越新权重越高）
                if age_days > expiry_days:
                    # 超过过期时间，权重为0
                    continue

                time_weight = 1.0 - (age_days / expiry_days) * 0.5  # 最多衰减50%

                # 将权重存储在元数据中
                mem.metadata["time_weight"] = time_weight
                weighted_memories.append(mem)

            except Exception:
                # 如果时间解析失败，使用默认权重
                mem.metadata["time_weight"] = 0.5
                weighted_memories.append(mem)

        # 按时间权重排序（这里简化处理，实际可以结合相似度分数）
        weighted_memories.sort(
            key=lambda x: x.metadata.get("time_weight", 0.5), reverse=True
        )

        return weighted_memories

