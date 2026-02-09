"""意图分类模块"""
from typing import Dict, Any, Optional
from enum import Enum
from ..utils.config import get_config
from ..utils.llm_factory import LLMFactory
import logging
import json

logger = logging.getLogger(__name__)


class QueryIntent(str, Enum):
    """查询意图类型"""
    FACTUAL = "factual"  # 事实查询
    COMPLEX_REASONING = "complex_reasoning"  # 复杂推理
    TOOL_CALL = "tool_call"  # 工具调用
    CONVERSATIONAL = "conversational"  # 对话
    UNKNOWN = "unknown"  # 未知


class IntentClassifier:
    """意图分类器"""

    INTENT_DESCRIPTIONS = {
        QueryIntent.FACTUAL: "简单的事实查询，可以直接从知识库中检索答案",
        QueryIntent.COMPLEX_REASONING: "需要多步推理的复杂问题，可能需要多次检索和逻辑推理",
        QueryIntent.TOOL_CALL: "需要调用外部工具（如搜索、数据库查询）的问题",
        QueryIntent.CONVERSATIONAL: "对话式查询，可能需要上下文记忆",
    }

    def __init__(self, config=None):
        """
        初始化意图分类器

        Args:
            config: 配置对象
        """
        if config is None:
            config = get_config()

        self.config = config

        self.llm = LLMFactory.create_llm(
            config=config,
            temperature=0.1,  # 低温度以获得更稳定的分类
        )

    def classify(
        self, query: str, return_confidence: bool = True
    ) -> Dict[str, Any]:
        """
        分类查询意图

        Args:
            query: 查询文本
            return_confidence: 是否返回置信度

        Returns:
            包含意图类型和可选置信度的字典
        """
        if not self.config.query.enable_intent_classification:
            return {
                "intent": QueryIntent.FACTUAL,
                "confidence": 1.0,
            }

        prompt = self._build_classification_prompt(query)

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            
            # 解析 JSON 响应
            result = self._parse_classification_result(content)
            
            logger.info(f"意图分类: {query} -> {result['intent']} (置信度: {result.get('confidence', 0.0)})")
            return result

        except Exception as e:
            logger.warning(f"意图分类失败，使用默认分类: {e}")
            return {
                "intent": QueryIntent.FACTUAL,
                "confidence": 0.5,
            }

    def _build_classification_prompt(self, query: str) -> str:
        """构建分类提示"""
        intent_list = "\n".join(
            [
                f"- {intent.value}: {desc}"
                for intent, desc in self.INTENT_DESCRIPTIONS.items()
            ]
        )

        prompt = f"""请对以下查询进行意图分类。

查询：{query}

可选的意图类型：
{intent_list}

请以 JSON 格式返回分类结果，包含以下字段：
- intent: 意图类型（必须是上述类型之一）
- confidence: 置信度（0-1之间的浮点数）
- reasoning: 简要说明分类理由

返回格式：
{{"intent": "factual", "confidence": 0.9, "reasoning": "这是一个简单的事实查询"}}"""

        return prompt

    def _parse_classification_result(self, content: str) -> Dict[str, Any]:
        """解析分类结果"""
        # 尝试提取 JSON
        content = content.strip()
        
        # 如果内容包含代码块，提取 JSON 部分
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            content = content[start:end].strip()

        try:
            result = json.loads(content)
            
            # 验证意图类型
            intent_str = result.get("intent", "factual")
            try:
                intent = QueryIntent(intent_str)
            except ValueError:
                intent = QueryIntent.UNKNOWN

            return {
                "intent": intent,
                "confidence": float(result.get("confidence", 0.5)),
                "reasoning": result.get("reasoning", ""),
            }

        except json.JSONDecodeError:
            # 如果 JSON 解析失败，尝试从文本中提取
            logger.warning("JSON 解析失败，尝试文本解析")
            
            # 简单的文本匹配
            content_lower = content.lower()
            if "factual" in content_lower or "事实" in content_lower:
                intent = QueryIntent.FACTUAL
            elif "complex" in content_lower or "复杂" in content_lower or "reasoning" in content_lower:
                intent = QueryIntent.COMPLEX_REASONING
            elif "tool" in content_lower or "工具" in content_lower:
                intent = QueryIntent.TOOL_CALL
            elif "conversational" in content_lower or "对话" in content_lower:
                intent = QueryIntent.CONVERSATIONAL
            else:
                intent = QueryIntent.UNKNOWN

            return {
                "intent": intent,
                "confidence": 0.7,
                "reasoning": "基于文本匹配的分类",
            }

