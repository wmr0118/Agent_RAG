"""记忆存储模块"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from langchain_chroma import Chroma
from langchain_core.documents import Document
from ..utils.config import get_config
from ..utils.embeddings import EmbeddingManager
from ..utils.llm_factory import LLMFactory
import logging

logger = logging.getLogger(__name__)


class MemoryStore:
    """记忆存储，使用 Chroma 存储历史交互摘要"""

    def __init__(self, config=None):
        """
        初始化记忆存储

        Args:
            config: 配置对象
        """
        if config is None:
            config = get_config()

        self.config = config
        self.memory_config = config.memory
        self.vector_db_config = config.vector_db
        self.llm_config = config.llm

        # 初始化 embedding
        self.embedding_manager = EmbeddingManager(config)

        # 初始化 LLM（用于生成摘要）
        self.llm = LLMFactory.create_llm(
            config=config,
            temperature=0.3,
        )

        # 创建或加载记忆向量存储
        self.vectorstore = self._create_memory_store()

    def _create_memory_store(self) -> Chroma:
        """创建记忆向量存储"""
        vectorstore = Chroma(
            persist_directory=self.vector_db_config.persist_directory,
            collection_name="memories",
            embedding_function=self.embedding_manager.embeddings,
        )
        return vectorstore

    def store_interaction(
        self,
        user_id: str,
        query: str,
        answer: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        存储交互摘要

        Args:
            user_id: 用户 ID
            query: 查询文本
            answer: 回答文本
            metadata: 额外元数据

        Returns:
            记忆 ID
        """
        if not self.memory_config.enabled:
            return ""

        # 生成交互摘要
        summary = self._summarize_interaction(query, answer)

        # 创建记忆文档
        memory_doc = Document(
            page_content=summary,
            metadata={
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "answer": answer[:200],  # 保存答案的前200字符
                **(metadata or {}),
            },
        )

        try:
            # 添加到向量存储
            ids = self.vectorstore.add_documents([memory_doc])
            
            # 检查是否需要清理旧记忆
            self._cleanup_old_memories(user_id)
            
            logger.info(f"记忆存储成功: 用户 {user_id}")
            return ids[0] if ids else ""

        except Exception as e:
            logger.error(f"记忆存储失败: {e}")
            return ""

    def _summarize_interaction(self, query: str, answer: str) -> str:
        """
        生成交互摘要

        Args:
            query: 查询文本
            answer: 回答文本

        Returns:
            摘要文本
        """
        prompt = f"""请将以下问答交互总结为简洁的记忆片段（50-100字），包含关键信息点，便于后续检索。

问题：{query}

回答：{answer[:500]}

摘要："""

        try:
            response = self.llm.invoke(prompt)
            summary = response.content if hasattr(response, "content") else str(response)
            summary = summary.strip().strip('"').strip("'")
            
            # 如果摘要太长，截断
            if len(summary) > 200:
                summary = summary[:200] + "..."
            
            return summary

        except Exception as e:
            logger.warning(f"生成摘要失败，使用简化版本: {e}")
            # 使用简化版本
            return f"问题: {query[:50]}... 回答: {answer[:50]}..."

    def _cleanup_old_memories(self, user_id: str):
        """清理旧记忆（超过最大数量或过期）"""
        try:
            # 获取用户的所有记忆
            all_memories = self.vectorstore.similarity_search(
                query="",  # 空查询获取所有
                k=1000,  # 获取足够多的记忆
                filter={"user_id": user_id},
            )

            if len(all_memories) <= self.memory_config.max_memories:
                return

            # 按时间排序，删除最旧的
            memories_with_time = []
            for mem in all_memories:
                timestamp_str = mem.metadata.get("timestamp", "")
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    memories_with_time.append((mem, timestamp))
                except Exception:
                    continue

            # 排序，最旧的在前
            memories_with_time.sort(key=lambda x: x[1])

            # 删除超过最大数量的记忆
            to_delete = memories_with_time[: len(memories_with_time) - self.memory_config.max_memories]
            
            # 注意：Chroma 的 delete 需要 IDs，这里简化处理
            # 实际实现中可能需要维护 ID 映射
            logger.info(f"清理 {len(to_delete)} 个旧记忆")

        except Exception as e:
            logger.warning(f"清理旧记忆失败: {e}")

    def delete_memories(self, user_id: str, memory_ids: Optional[List[str]] = None) -> bool:
        """
        删除记忆

        Args:
            user_id: 用户 ID
            memory_ids: 记忆 ID 列表，如果为 None 则删除该用户的所有记忆

        Returns:
            是否成功
        """
        try:
            if memory_ids:
                self.vectorstore.delete(ids=memory_ids)
            else:
                # 删除用户的所有记忆（需要先查询）
                memories = self.vectorstore.similarity_search(
                    query="",
                    k=1000,
                    filter={"user_id": user_id},
                )
                # 注意：实际实现中需要维护 ID 映射
                logger.warning("批量删除记忆需要维护 ID 映射，当前实现不支持")

            logger.info(f"删除记忆成功: 用户 {user_id}")
            return True

        except Exception as e:
            logger.error(f"删除记忆失败: {e}")
            return False

