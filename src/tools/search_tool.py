"""Bing 搜索工具"""
from typing import Any, Optional
import requests
from .tool_registry import BaseTool
from ..utils.config import get_config
import logging

logger = logging.getLogger(__name__)


class BingSearchTool(BaseTool):
    """Bing 搜索工具"""

    @property
    def name(self) -> str:
        return "bing_search"

    @property
    def description(self) -> str:
        return "使用 Bing 搜索获取最新信息。参数：搜索查询字符串。"

    def __init__(self, config=None):
        """
        初始化 Bing 搜索工具

        Args:
            config: 配置对象
        """
        if config is None:
            config = get_config()

        self.config = config
        tools_config = config.tools.bing_search

        if not tools_config.get("enabled", False):
            raise ValueError("Bing 搜索工具未启用")

        self.api_key = tools_config.get("api_key") or None
        self.endpoint = tools_config.get("endpoint", "https://api.bing.microsoft.com/v7.0/search")

        if not self.api_key:
            raise ValueError("Bing API key 未配置")

    def execute(self, params: str, query: str) -> str:
        """
        执行搜索

        Args:
            params: 搜索查询字符串
            query: 原始查询（如果 params 为空则使用）

        Returns:
            搜索结果摘要
        """
        search_query = params.strip() if params.strip() else query

        try:
            headers = {
                "Ocp-Apim-Subscription-Key": self.api_key,
            }
            params_dict = {
                "q": search_query,
                "count": 5,  # 返回前5个结果
                "textDecorations": False,
                "textFormat": "Raw",
            }

            response = requests.get(self.endpoint, headers=headers, params=params_dict)
            response.raise_for_status()

            data = response.json()
            results = data.get("webPages", {}).get("value", [])

            # 格式化结果
            formatted_results = []
            for i, result in enumerate(results, 1):
                title = result.get("name", "")
                snippet = result.get("snippet", "")
                url = result.get("url", "")
                formatted_results.append(f"{i}. {title}\n   {snippet}\n   {url}")

            result_text = "\n\n".join(formatted_results)
            logger.info(f"Bing 搜索成功: {search_query}, 找到 {len(results)} 个结果")
            
            return f"搜索结果（查询: {search_query}）:\n\n{result_text}"

        except Exception as e:
            logger.error(f"Bing 搜索失败: {e}")
            return f"搜索失败: {str(e)}"

