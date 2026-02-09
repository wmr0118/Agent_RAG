"""RAG 链组装"""
from typing import List, Optional, Dict, Any
from langchain_core.documents import Document
from .retriever import BaseRetriever
from .generator import AnswerGenerator
from ..utils.config import get_config
from ..tools.tool_registry import ToolRegistry
import logging

logger = logging.getLogger(__name__)


class RAGChain:
    """RAG 链，组装检索和生成流程"""

    def __init__(
        self,
        retriever: Optional[BaseRetriever] = None,
        generator: Optional[AnswerGenerator] = None,
        tool_registry: Optional[ToolRegistry] = None,
        config=None,
    ):
        """
        初始化 RAG 链

        Args:
            retriever: 检索器，如果为 None 则创建新的
            generator: 生成器，如果为 None 则创建新的
            tool_registry: 工具注册表，用于自动工具调用
            config: 配置对象
        """
        if config is None:
            config = get_config()

        self.config = config

        # 初始化组件
        self.retriever = retriever or BaseRetriever(config=config)
        self.generator = generator or AnswerGenerator(config=config)
        self.tool_registry = tool_registry

    def query(
        self,
        question: str,
        top_k: Optional[int] = None,
        additional_context: Optional[str] = None,
        return_sources: bool = False,
        enable_tool_fallback: bool = True,
        allow_general_knowledge: bool = False,
    ) -> str | Dict[str, Any]:
        """
        执行查询

        Args:
            question: 问题
            top_k: 检索的文档数量
            additional_context: 额外的上下文（如记忆）
            return_sources: 是否返回来源信息
            enable_tool_fallback: 是否启用工具回退（知识库无答案时调用工具）
            allow_general_knowledge: 是否允许使用通用知识

        Returns:
            答案字符串或包含答案和来源的字典
        """
        # 1. 检索相关文档
        logger.info(f"开始检索问题: {question}")
        documents = self.retriever.retrieve(question, top_k=top_k)

        if not documents:
            logger.warning("未检索到相关文档")
            # 如果启用工具回退，尝试调用工具
            if enable_tool_fallback and self.tool_registry:
                tool_result = self._try_tool_call(question)
                if tool_result:
                    documents = [tool_result]
                else:
                    if allow_general_knowledge:
                        # 允许使用通用知识
                        pass
                    else:
                        return "抱歉，未找到相关信息。"

        # 2. 生成答案
        logger.info("开始生成答案")
        if return_sources:
            result = self.generator.generate_with_metadata(
                question, documents, additional_context, allow_general_knowledge
            )
        else:
            answer = self.generator.generate(
                question, documents, additional_context, allow_general_knowledge
            )
            result = answer

        # 3. 检测是否需要工具调用
        if enable_tool_fallback and self.tool_registry:
            if self._should_use_tool(result, documents):
                tool_result = self._try_tool_call(question, result)
                if tool_result:
                    # 将工具结果加入上下文，重新生成答案
                    documents.append(tool_result)
                    logger.info("工具调用成功，重新生成答案")
                    if return_sources:
                        result = self.generator.generate_with_metadata(
                            question, documents, additional_context, allow_general_knowledge
                        )
                    else:
                        answer = self.generator.generate(
                            question, documents, additional_context, allow_general_knowledge
                        )
                        result = answer

        logger.info("RAG 查询完成")
        return result
    
    def _should_use_tool(self, result: str | Dict[str, Any], documents: List[Document]) -> bool:
        """
        检测是否应该调用工具
        
        Args:
            result: 当前答案结果
            documents: 检索到的文档
            
        Returns:
            是否应该调用工具
        """
        # 提取答案文本
        if isinstance(result, dict):
            answer = result.get("answer", "")
        else:
            answer = str(result)
        
        # 检测"无法找到答案"的关键词
        no_answer_keywords = [
            "无法从提供的上下文中找到答案",
            "无法找到相关信息",
            "抱歉，未找到相关信息",
            "不知道",
            "无法回答",
        ]
        
        has_no_answer = any(keyword in answer for keyword in no_answer_keywords)
        has_low_relevance = len(documents) == 0
        
        return has_no_answer or has_low_relevance
    
    def _try_tool_call(self, question: str, current_result: Optional[str | Dict[str, Any]] = None) -> Optional[Document]:
        """
        尝试调用工具
        
        Args:
            question: 问题
            current_result: 当前答案结果（可选）
            
        Returns:
            工具结果文档，如果失败返回None
        """
        if not self.tool_registry:
            return None
        
        try:
            # 1. 判断应该调用哪个工具
            tool_name = self._select_tool(question)
            
            if not tool_name:
                return None
            
            # 2. 调用工具
            tool_result = self.tool_registry.call_tool(tool_name, question, question)
            
            # 3. 转换为文档格式
            result_doc = Document(
                page_content=str(tool_result),
                metadata={"source": f"tool:{tool_name}", "tool": tool_name}
            )
            
            logger.info(f"工具调用成功: {tool_name}")
            return result_doc
            
        except Exception as e:
            logger.warning(f"工具调用失败: {e}")
            return None
    
    def _select_tool(self, question: str) -> Optional[str]:
        """
        根据问题选择工具
        
        Args:
            question: 问题
            
        Returns:
            工具名称，如果不需要工具返回None
        """
        if not self.tool_registry:
            return None
        
        available_tools = self.tool_registry.list_tools()
        
        # 简单规则：包含"查询"、"数据"等关键词 -> 数据库
        # 其他 -> Bing搜索
        db_keywords = ["查询", "数据", "统计", "数据库", "sql", "表", "记录"]
        if any(keyword in question for keyword in db_keywords) and "database" in available_tools:
            return "database"
        
        # 检查Bing搜索是否可用
        if "bing_search" in available_tools:
            return "bing_search"
        
        return None

    def query_with_expansion(
        self,
        question: str,
        original_top_k: int = 5,
        expansion_factor: int = 4,
        additional_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        使用扩展检索的查询（用于二次检索场景）

        Args:
            question: 问题
            original_top_k: 原始 top_k
            expansion_factor: 扩展因子
            additional_context: 额外的上下文

        Returns:
            包含答案和来源的字典
        """
        # 扩大检索范围
        documents = self.retriever.expand_retrieval(
            question, original_top_k, expansion_factor
        )

        if not documents:
            return {
                "answer": "抱歉，未找到相关信息。",
                "sources": [],
                "num_sources": 0,
            }

        # 生成答案
        result = self.generator.generate_with_metadata(
            question, documents, additional_context
        )

        return result

    def add_documents(self, documents: List[Document]) -> List[str]:
        """
        添加文档到知识库

        Args:
            documents: 文档列表

        Returns:
            文档 ID 列表
        """
        return self.retriever.add_documents(documents)

