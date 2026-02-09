"""数据库查询工具"""
from typing import Any, Optional, List, Dict
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from .tool_registry import BaseTool
from ..utils.config import get_config
import logging

logger = logging.getLogger(__name__)


class DatabaseTool(BaseTool):
    """数据库查询工具"""

    @property
    def name(self) -> str:
        return "database_query"

    @property
    def description(self) -> str:
        return "执行 SQL 查询从数据库获取数据。参数：SQL 查询语句。"

    def __init__(self, config=None):
        """
        初始化数据库工具

        Args:
            config: 配置对象
        """
        if config is None:
            config = get_config()

        self.config = config
        tools_config = config.tools.database

        if not tools_config.get("enabled", False):
            raise ValueError("数据库工具未启用")

        connection_string = tools_config.get("connection_string") or None

        if not connection_string:
            raise ValueError("数据库连接字符串未配置")

        try:
            self.engine: Engine = create_engine(connection_string)
            logger.info("数据库连接成功")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise

    def execute(self, params: str, query: str) -> str:
        """
        执行 SQL 查询

        Args:
            params: SQL 查询语句
            query: 原始查询（用于上下文）

        Returns:
            查询结果（格式化的字符串）
        """
        sql_query = params.strip()

        if not sql_query:
            return "错误: SQL 查询语句为空"

        # 安全检查：只允许 SELECT 语句
        sql_upper = sql_query.upper().strip()
        if not sql_upper.startswith("SELECT"):
            return "错误: 只允许执行 SELECT 查询"

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql_query))
                rows = result.fetchall()
                columns = result.keys()

                # 格式化结果
                if not rows:
                    return "查询结果为空"

                # 转换为字典列表
                formatted_rows = []
                for row in rows[:100]:  # 限制返回100行
                    row_dict = dict(zip(columns, row))
                    formatted_rows.append(row_dict)

                # 格式化为字符串
                result_text = f"查询结果（共 {len(rows)} 行，显示前 {min(len(rows), 100)} 行）:\n\n"
                
                # 表头
                if formatted_rows:
                    headers = list(formatted_rows[0].keys())
                    result_text += " | ".join(headers) + "\n"
                    result_text += "-" * (len(" | ".join(headers))) + "\n"
                    
                    # 数据行
                    for row_dict in formatted_rows[:10]:  # 只显示前10行
                        values = [str(row_dict.get(col, ""))[:50] for col in headers]
                        result_text += " | ".join(values) + "\n"
                    
                    if len(formatted_rows) > 10:
                        result_text += f"\n... 还有 {len(formatted_rows) - 10} 行数据"

                logger.info(f"数据库查询成功: {sql_query[:50]}..., 返回 {len(rows)} 行")
                return result_text

        except Exception as e:
            logger.error(f"数据库查询失败: {e}")
            return f"查询失败: {str(e)}"

    def get_schema(self, table_name: Optional[str] = None) -> str:
        """
        获取数据库表结构

        Args:
            table_name: 表名，如果为 None 则返回所有表

        Returns:
            表结构信息
        """
        try:
            with self.engine.connect() as conn:
                if table_name:
                    # 获取特定表的结构
                    query = f"DESCRIBE {table_name}"
                    result = conn.execute(text(query))
                    rows = result.fetchall()
                    return f"表 {table_name} 的结构:\n{rows}"
                else:
                    # 获取所有表名
                    if self.engine.dialect.name == "sqlite":
                        query = "SELECT name FROM sqlite_master WHERE type='table'"
                    elif self.engine.dialect.name == "postgresql":
                        query = "SELECT tablename FROM pg_tables WHERE schemaname='public'"
                    else:
                        query = "SHOW TABLES"

                    result = conn.execute(text(query))
                    tables = [row[0] for row in result.fetchall()]
                    return f"数据库中的表: {', '.join(tables)}"

        except Exception as e:
            logger.error(f"获取表结构失败: {e}")
            return f"获取表结构失败: {str(e)}"

