"""推理逻辑模块"""
from typing import Dict, Any, Optional, List
from langchain_core.documents import Document
from ..utils.config import get_config
from ..utils.llm_factory import LLMFactory
import logging
import re

logger = logging.getLogger(__name__)


class ReasoningEngine:
    """推理引擎，负责提取推理步骤、计算置信度、验证一致性"""

    def __init__(self, config=None):
        """
        初始化推理引擎

        Args:
            config: 配置对象
        """
        if config is None:
            config = get_config()

        self.config = config
        self.agent_config = config.agent

        self.llm = LLMFactory.create_llm(
            config=config,
            temperature=0.7,
        )

        self.confidence_threshold = self.agent_config.confidence_threshold

    def reason(
        self,
        query: str,
        context: List[Document],
        previous_reasoning: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        执行推理，生成推理步骤和动作

        Args:
            query: 查询文本
            context: 当前上下文文档
            previous_reasoning: 之前的推理步骤

        Returns:
            包含推理步骤、动作和置信度的字典
        """
        prompt = self._build_reasoning_prompt(query, context, previous_reasoning)

        try:
            response = self.llm.invoke(prompt)
            reasoning_text = response.content if hasattr(response, "content") else str(response)

            # 解析推理结果
            result = self._parse_reasoning(reasoning_text)
            
            logger.debug(f"推理完成: {result.get('action', 'unknown')}")
            return result

        except Exception as e:
            logger.error(f"推理失败: {e}")
            return {
                "thought": f"推理过程出错: {e}",
                "action": "answer",
                "action_input": "",
                "confidence": 0.3,
            }

    def extract_confidence(self, reasoning_text: str) -> float:
        """
        从推理文本中提取置信度

        Args:
            reasoning_text: 推理文本

        Returns:
            置信度分数（0-1）
        """
        # 尝试从文本中提取数字
        confidence_patterns = [
            r"置信度[：:]\s*([0-9.]+)",
            r"confidence[：:]\s*([0-9.]+)",
            r"confidence[：:]\s*(\d+)%",
            r"(\d+\.\d+)\s*分",
        ]

        for pattern in confidence_patterns:
            match = re.search(pattern, reasoning_text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                # 如果是百分比，转换为小数
                if "%" in match.group(0) or value > 1:
                    value = value / 100.0
                return min(max(value, 0.0), 1.0)

        # 如果没有找到明确的置信度，根据关键词估算
        text_lower = reasoning_text.lower()
        if any(word in text_lower for word in ["不确定", "不清楚", "unknown", "uncertain"]):
            return 0.3
        elif any(word in text_lower for word in ["可能", "maybe", "perhaps"]):
            return 0.5
        elif any(word in text_lower for word in ["确定", "certain", "sure", "definitely"]):
            return 0.9
        else:
            return 0.7  # 默认中等置信度

    def validate_answer(
        self,
        query: str,
        reasoning: str,
        answer: str,
        context: List[Document],
    ) -> Dict[str, Any]:
        """
        验证答案与推理的一致性

        Args:
            query: 原始查询
            reasoning: 推理过程
            answer: 生成的答案
            context: 上下文文档

        Returns:
            验证结果字典
        """
        prompt = f"""请评估以下答案的质量和一致性。

问题：{query}

推理过程：
{reasoning}

生成的答案：
{answer}

检索到的证据：
{self._format_context(context)}

请评估：
1. 答案是否与推理过程一致？
2. 答案是否被证据支持？
3. 答案质量评分（0-1）

请以 JSON 格式返回：
{{
    "consistent": true/false,
    "score": 0.0-1.0,
    "reason": "评估理由"
}}"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)

            # 解析 JSON
            result = self._parse_validation_result(content)
            
            logger.info(f"答案验证: 一致性={result['consistent']}, 分数={result['score']}")
            return result

        except Exception as e:
            logger.warning(f"答案验证失败: {e}")
            return {
                "consistent": True,  # 默认通过
                "score": 0.7,
                "reason": f"验证过程出错: {e}",
            }

    def _build_reasoning_prompt(
        self,
        query: str,
        context: List[Document],
        previous_reasoning: Optional[str] = None,
    ) -> str:
        """构建推理提示"""
        context_text = self._format_context(context)

        prompt = f"""你是一个智能助手，需要基于给定的上下文回答问题。

问题：{query}

当前上下文：
{context_text}

"""

        if previous_reasoning:
            prompt += f"""
之前的推理步骤：
{previous_reasoning}

"""

        prompt += """请按照以下格式进行推理：

思考（Thought）：分析当前情况，评估是否有足够的信息回答问题。如果没有，说明需要什么信息。
动作（Action）：选择下一步动作。可选动作：
- search: 需要检索更多信息
- answer: 有足够信息，可以回答问题
- tool_call: 需要调用工具（如搜索、数据库查询）

动作输入（Action Input）：如果是 search，提供检索查询；如果是 answer，提供答案；如果是 tool_call，提供工具名称和参数。

置信度（Confidence）：评估当前答案的置信度（0-1之间的浮点数）。

请按以下格式输出：
思考：...
动作：search/answer/tool_call
动作输入：...
置信度：0.8"""

        return prompt

    def _parse_reasoning(self, reasoning_text: str) -> Dict[str, Any]:
        """解析推理结果"""
        result = {
            "thought": "",
            "action": "answer",
            "action_input": "",
            "confidence": 0.7,
        }

        # 提取思考
        thought_match = re.search(r"思考[：:]\s*(.+?)(?=动作|$)", reasoning_text, re.DOTALL)
        if thought_match:
            result["thought"] = thought_match.group(1).strip()

        # 提取动作
        action_match = re.search(r"动作[：:]\s*(search|answer|tool_call)", reasoning_text, re.IGNORECASE)
        if action_match:
            result["action"] = action_match.group(1).lower()

        # 提取动作输入
        action_input_match = re.search(
            r"动作输入[：:]\s*(.+?)(?=置信度|$)", reasoning_text, re.DOTALL
        )
        if action_input_match:
            result["action_input"] = action_input_match.group(1).strip()

        # 提取置信度
        result["confidence"] = self.extract_confidence(reasoning_text)

        return result

    def _parse_validation_result(self, content: str) -> Dict[str, Any]:
        """解析验证结果"""
        # 尝试提取 JSON
        content = content.strip()
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            content = content[start:end].strip()

        try:
            import json
            result = json.loads(content)
            return {
                "consistent": bool(result.get("consistent", True)),
                "score": float(result.get("score", 0.7)),
                "reason": result.get("reason", ""),
            }
        except Exception:
            # 如果解析失败，使用文本匹配
            content_lower = content.lower()
            consistent = "不一致" not in content_lower and "inconsistent" not in content_lower
            score = 0.7 if consistent else 0.3

            return {
                "consistent": consistent,
                "score": score,
                "reason": "基于文本匹配的验证",
            }

    def _format_context(self, documents: List[Document]) -> str:
        """格式化上下文"""
        parts = []
        for i, doc in enumerate(documents, 1):
            parts.append(f"[文档{i}]\n{doc.page_content[:500]}")
        return "\n\n".join(parts)

