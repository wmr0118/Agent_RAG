"""动作执行器"""
from typing import Dict, Any, List, Optional
from langchain_core.documents import Document
from ..core.retriever import BaseRetriever
from ..core.generator import AnswerGenerator
from ..tools.tool_registry import ToolRegistry
from ..utils.config import get_config
import logging

logger = logging.getLogger(__name__)


class ActionExecutor:
    """动作执行器，执行检索、工具调用、回答等动作"""

    def __init__(
        self,
        retriever: Optional[BaseRetriever] = None,
        generator: Optional[AnswerGenerator] = None,
        tool_registry: Optional[ToolRegistry] = None,
        config=None,
    ):
        """
        初始化动作执行器

        Args:
            retriever: 检索器
            generator: 生成器
            tool_registry: 工具注册表
            config: 配置对象
        """
        if config is None:
            config = get_config()

        self.config = config
        self.retriever = retriever
        self.generator = generator
        self.tool_registry = tool_registry

    def execute(
        self,
        action: str,
        action_input: str,
        query: str,
        context: List[Document],
    ) -> Dict[str, Any]:
        """
        执行动作

        Args:
            action: 动作类型（search/answer/tool_call）
            action_input: 动作输入
            query: 原始查询
            context: 当前上下文

        Returns:
            执行结果字典
        """
        if action == "search":
            return self._execute_search(action_input, query, context)
        elif action == "answer":
            return self._execute_answer(action_input, query, context)
        elif action == "tool_call":
            return self._execute_tool_call(action_input, query, context)
        else:
            logger.warning(f"未知动作: {action}")
            return {
                "status": "error",
                "result": f"未知动作: {action}",
                "documents": [],
            }

    def _execute_search(
        self,
        search_query: str,
        original_query: str,
        context: List[Document],
    ) -> Dict[str, Any]:
        """
        执行检索动作

        Args:
            search_query: 检索查询
            original_query: 原始查询
            context: 当前上下文

        Returns:
            检索结果
        """
        if not self.retriever:
            return {
                "status": "error",
                "result": "检索器未初始化",
                "documents": [],
            }

        # 如果 search_query 为空，使用原始查询
        query = search_query.strip() if search_query.strip() else original_query

        try:
            # 执行检索
            documents = self.retriever.retrieve(query)
            
            logger.info(f"检索动作执行成功: 找到 {len(documents)} 个文档")
            
            return {
                "status": "success",
                "result": f"检索到 {len(documents)} 个相关文档",
                "documents": documents,
                "query_used": query,
            }

        except Exception as e:
            logger.error(f"检索动作执行失败: {e}")
            return {
                "status": "error",
                "result": f"检索失败: {e}",
                "documents": [],
            }

    def _execute_answer(
        self,
        answer_input: str,
        query: str,
        context: List[Document],
    ) -> Dict[str, Any]:
        """
        执行回答动作

        Args:
            answer_input: 答案输入（可能是预生成的答案或空）
            query: 原始查询
            context: 上下文文档

        Returns:
            答案结果
        """
        if not self.generator:
            # 如果没有生成器，直接返回输入
            return {
                "status": "success",
                "result": answer_input if answer_input else "无法生成答案",
                "documents": context,
            }

        try:
            # 如果已有答案输入，直接使用；否则生成
            if answer_input.strip():
                answer = answer_input
            else:
                answer = self.generator.generate(query, context)

            logger.info("回答动作执行成功")
            
            return {
                "status": "success",
                "result": answer,
                "documents": context,
            }

        except Exception as e:
            logger.error(f"回答动作执行失败: {e}")
            return {
                "status": "error",
                "result": f"生成答案失败: {e}",
                "documents": context,
            }

    def _execute_tool_call(
        self,
        tool_input: str,
        query: str,
        context: List[Document],
    ) -> Dict[str, Any]:
        """
        执行工具调用动作

        Args:
            tool_input: 工具输入（格式：tool_name:params）
            query: 原始查询
            context: 上下文文档

        Returns:
            工具调用结果
        """
        if not self.tool_registry:
            return {
                "status": "error",
                "result": "工具注册表未初始化",
                "documents": [],
            }

        try:
            # 解析工具输入
            parts = tool_input.split(":", 1)
            tool_name = parts[0].strip()
            tool_params = parts[1].strip() if len(parts) > 1 else ""

            # 调用工具
            tool_result = self.tool_registry.call_tool(tool_name, tool_params, query)

            # 将工具结果转换为文档格式
            result_doc = Document(
                page_content=str(tool_result),
                metadata={"source": f"tool:{tool_name}", "tool": tool_name},
            )

            logger.info(f"工具调用成功: {tool_name}")
            
            return {
                "status": "success",
                "result": str(tool_result),
                "documents": [result_doc],
                "tool_name": tool_name,
            }

        except Exception as e:
            logger.error(f"工具调用失败: {e}")
            return {
                "status": "error",
                "result": f"工具调用失败: {e}",
                "documents": [],
            }

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
        if not self.retriever:
            return []

        return self.retriever.expand_retrieval(query, original_top_k, expansion_factor)

