"""答案生成器"""
from typing import List, Optional, Dict, Any
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_core.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from ..utils.config import get_config
from ..utils.llm_factory import LLMFactory
import logging

logger = logging.getLogger(__name__)


class AnswerGenerator:
    """答案生成器"""

    DEFAULT_PROMPT_TEMPLATE = """基于以下上下文信息回答问题。如果上下文中没有相关信息，请说明无法从提供的上下文中找到答案。

上下文信息：
{context}

问题：{question}

请提供准确、完整的答案："""

    HYBRID_PROMPT_TEMPLATE = """基于以下上下文信息回答问题。

上下文信息：
{context}

问题：{question}

回答规则：
1. 如果上下文中包含相关信息，优先基于上下文回答，并标注来源
2. 如果上下文中没有相关信息，但问题是关于通用知识的，可以使用你的通用知识回答，但需要明确说明"这是基于通用知识，不是来自知识库"
3. 如果问题既不在上下文中，也不是通用知识问题，请说明无法回答

请提供准确、完整的答案："""

    def __init__(
        self,
        config=None,
        prompt_template: Optional[str] = None,
        streaming: bool = False,
        mode: str = "strict",
    ):
        """
        初始化答案生成器

        Args:
            config: 配置对象
            prompt_template: Prompt 模板
            streaming: 是否启用流式输出
            mode: 模式，"strict"（严格模式，仅基于知识库）或 "hybrid"（混合模式，允许通用知识）
        """
        if config is None:
            config = get_config()

        self.config = config
        self.mode = mode
        llm_config = config.llm

        # 初始化 LLM（使用工厂类，支持 OpenAI 和 Qwen）
        callbacks = [StreamingStdOutCallbackHandler()] if streaming else None
        self.llm = LLMFactory.create_llm(
            config=config,
            streaming=streaming,
            callbacks=callbacks,
        )

        # 设置 Prompt 模板
        if prompt_template:
            self.prompt_template = prompt_template
        elif mode == "hybrid":
            self.prompt_template = self.HYBRID_PROMPT_TEMPLATE
        else:
            self.prompt_template = self.DEFAULT_PROMPT_TEMPLATE
            
        self.prompt = PromptTemplate(
            input_variables=["context", "question"],
            template=self.prompt_template,
        )

    def generate(
        self,
        question: str,
        context: List[Document],
        additional_context: Optional[str] = None,
        allow_general_knowledge: Optional[bool] = None,
    ) -> str:
        """
        生成答案

        Args:
            question: 问题
            context: 检索到的上下文文档
            additional_context: 额外的上下文（如记忆）
            allow_general_knowledge: 是否允许使用通用知识（None时使用self.mode）

        Returns:
            生成的答案
        """
        # 决定是否使用混合模式
        use_hybrid = allow_general_knowledge if allow_general_knowledge is not None else (self.mode == "hybrid")
        
        # 检测上下文相关性
        has_relevant_context = self._check_context_relevance(context, question)
        
        # 如果使用混合模式且上下文相关性低，使用混合Prompt
        if use_hybrid and not has_relevant_context:
            prompt_template = self.HYBRID_PROMPT_TEMPLATE
        else:
            prompt_template = self.prompt_template
        
        # 格式化上下文
        context_text = self._format_context(context)

        # 如果有额外上下文，添加到上下文中
        if additional_context:
            context_text = f"{additional_context}\n\n{context_text}"

        # 构建完整的 prompt
        prompt = PromptTemplate(
            input_variables=["context", "question"],
            template=prompt_template,
        ).format(context=context_text, question=question)

        try:
            response = self.llm.invoke(prompt)
            answer = response.content if hasattr(response, "content") else str(response)
            
            logger.info("答案生成成功")
            return answer

        except Exception as e:
            logger.error(f"答案生成失败: {e}")
            raise
    
    def _check_context_relevance(self, context: List[Document], question: str) -> bool:
        """
        检查上下文是否相关
        
        Args:
            context: 上下文文档列表
            question: 问题
            
        Returns:
            是否相关
        """
        if not context:
            return False
        
        # 简单检查：如果文档数量为0或内容为空，认为不相关
        if len(context) == 0:
            return False
        
        # 检查文档内容是否为空
        total_content_length = sum(len(doc.page_content) for doc in context)
        if total_content_length < 50:  # 内容太少，认为不相关
            return False
        
        return True

    def generate_with_metadata(
        self,
        question: str,
        context: List[Document],
        additional_context: Optional[str] = None,
        allow_general_knowledge: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        生成答案（带元数据）

        Args:
            question: 问题
            context: 检索到的上下文文档
            additional_context: 额外的上下文
            allow_general_knowledge: 是否允许使用通用知识

        Returns:
            包含答案和元数据的字典
        """
        answer = self.generate(question, context, additional_context, allow_general_knowledge)

        return {
            "answer": answer,
            "sources": [doc.metadata.get("source", "unknown") for doc in context],
            "num_sources": len(context),
        }

    def _format_context(self, documents: List[Document]) -> str:
        """
        格式化上下文文档

        Args:
            documents: 文档列表

        Returns:
            格式化后的上下文文本
        """
        context_parts = []
        for i, doc in enumerate(documents, 1):
            source = doc.metadata.get("source", f"文档{i}")
            content = doc.page_content.strip()
            context_parts.append(f"[来源 {i}: {source}]\n{content}")

        return "\n\n".join(context_parts)

    def update_prompt_template(self, template: str):
        """
        更新 Prompt 模板

        Args:
            template: 新的模板字符串
        """
        self.prompt_template = template
        self.prompt = PromptTemplate(
            input_variables=["context", "question"],
            template=template,
        )
        logger.info("Prompt 模板已更新")

