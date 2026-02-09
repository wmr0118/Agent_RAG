"""LLM 工厂类，支持多种 LLM 提供商"""
from typing import Optional, Any
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatTongyi
from langchain_core.language_models import BaseChatModel
from .config import get_config
import logging

logger = logging.getLogger(__name__)


class LLMFactory:
    """LLM 工厂类，根据配置创建相应的 LLM 实例"""

    @staticmethod
    def create_llm(
        config=None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        api_key: Optional[str] = None,
        streaming: bool = False,
        callbacks: Optional[list] = None,
    ) -> BaseChatModel:
        """
        创建 LLM 实例

        Args:
            config: 配置对象
            model_name: 模型名称（覆盖配置）
            temperature: 温度参数（覆盖配置）
            max_tokens: 最大 token 数（覆盖配置）
            api_key: API key（覆盖配置）
            streaming: 是否流式输出
            callbacks: 回调函数列表

        Returns:
            LLM 实例
        """
        if config is None:
            config = get_config()

        llm_config = config.llm
        provider = llm_config.provider.lower()

        # 使用参数覆盖配置
        model_name = model_name or llm_config.model_name
        temperature = temperature if temperature is not None else llm_config.temperature
        max_tokens = max_tokens or llm_config.max_tokens
        api_key = api_key or llm_config.api_key

        # 检查 API key 是否有效
        if not api_key or api_key.startswith("${") or api_key.startswith("your_"):
            if provider == "openai":
                raise ValueError(
                    "OpenAI API key 未设置。请设置环境变量 OPENAI_API_KEY 或创建 .env 文件。\n"
                    "参考 .env.example 文件创建 .env 文件。"
                )
            elif provider == "qwen" or provider == "tongyi":
                raise ValueError(
                    "DashScope API key 未设置。请设置环境变量 DASHSCOPE_API_KEY 或创建 .env 文件。\n"
                    "获取 API key: https://dashscope.console.aliyun.com/\n"
                    "参考 .env.example 文件创建 .env 文件。"
                )
        
        if provider == "openai":
            return LLMFactory._create_openai_llm(
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=api_key,
                streaming=streaming,
                callbacks=callbacks,
            )
        elif provider == "qwen" or provider == "tongyi":
            return LLMFactory._create_qwen_llm(
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=api_key,
                streaming=streaming,
                callbacks=callbacks,
            )
        else:
            raise ValueError(f"不支持的 LLM 提供商: {provider}")

    @staticmethod
    def _create_openai_llm(
        model_name: str,
        temperature: float,
        max_tokens: int,
        api_key: Optional[str],
        streaming: bool,
        callbacks: Optional[list],
    ) -> ChatOpenAI:
        """创建 OpenAI LLM"""
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key,
            streaming=streaming,
            callbacks=callbacks,
        )

    @staticmethod
    def _create_qwen_llm(
        model_name: str,
        temperature: float,
        max_tokens: int,
        api_key: Optional[str],
        streaming: bool,
        callbacks: Optional[list],
    ) -> ChatTongyi:
        """创建 Qwen (Tongyi) LLM"""
        return ChatTongyi(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            dashscope_api_key=api_key,
            streaming=streaming,
            callbacks=callbacks,
        )

