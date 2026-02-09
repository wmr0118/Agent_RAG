"""工具注册表"""
from typing import Dict, Any, Optional, Callable
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """工具基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        pass

    @abstractmethod
    def execute(self, params: str, query: str) -> Any:
        """
        执行工具

        Args:
            params: 参数字符串
            query: 原始查询

        Returns:
            工具执行结果
        """
        pass


class ToolRegistry:
    """工具注册表，管理所有可用工具"""

    def __init__(self):
        """初始化工具注册表"""
        self.tools: Dict[str, BaseTool] = {}

    def register_tool(self, tool: BaseTool):
        """
        注册工具

        Args:
            tool: 工具对象
        """
        self.tools[tool.name] = tool
        logger.info(f"工具注册成功: {tool.name}")

    def unregister_tool(self, tool_name: str):
        """
        注销工具

        Args:
            tool_name: 工具名称
        """
        if tool_name in self.tools:
            del self.tools[tool_name]
            logger.info(f"工具注销成功: {tool_name}")

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        获取工具

        Args:
            tool_name: 工具名称

        Returns:
            工具对象，如果不存在返回 None
        """
        return self.tools.get(tool_name)

    def list_tools(self) -> Dict[str, str]:
        """
        列出所有工具

        Returns:
            工具名称到描述的映射
        """
        return {name: tool.description for name, tool in self.tools.items()}

    def call_tool(self, tool_name: str, params: str, query: str) -> Any:
        """
        调用工具

        Args:
            tool_name: 工具名称
            params: 参数字符串
            query: 原始查询

        Returns:
            工具执行结果
        """
        tool = self.get_tool(tool_name)
        if tool is None:
            raise ValueError(f"工具不存在: {tool_name}")

        try:
            result = tool.execute(params, query)
            logger.info(f"工具调用成功: {tool_name}")
            return result
        except Exception as e:
            logger.error(f"工具调用失败: {tool_name}, 错误: {e}")
            raise

    def get_tool_descriptions(self) -> str:
        """
        获取所有工具的描述（用于 Agent 提示）

        Returns:
            工具描述字符串
        """
        descriptions = []
        for name, tool in self.tools.items():
            descriptions.append(f"- {name}: {tool.description}")
        return "\n".join(descriptions)

