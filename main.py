"""Agent-RAG 问答系统主入口"""
import asyncio
import argparse
import logging
from pathlib import Path
from src.utils.config import get_config
from src.core.rag_chain import RAGChain
from src.agent.react_agent import ReActAgent
from src.query.query_router import QueryRouter
from src.memory.memory_retriever import MemoryRetriever
from src.memory.memory_store import MemoryStore
from src.tools.tool_registry import ToolRegistry
from src.tools.search_tool import BingSearchTool
from src.tools.db_tool import DatabaseTool
from src.indexing.index_manager import IndexManager
from src.indexing.document_loader import DocumentLoader
from src.indexing.text_splitter import TextSplitter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class RAGSystem:
    """RAG 系统主类"""

    def __init__(self, config_path: str = None):
        """
        初始化 RAG 系统

        Args:
            config_path: 配置文件路径
        """
        self.config = get_config(config_path)
        
        # 初始化工具（先初始化，因为RAG Chain可能需要）
        self.tool_registry = ToolRegistry()
        self._register_tools()
        
        # 初始化核心组件（传递工具注册表）
        self.rag_chain = RAGChain(
            config=self.config,
            tool_registry=self.tool_registry
        )
        self.query_router = QueryRouter(config=self.config, basic_rag=self.rag_chain)
        
        # 初始化记忆机制
        self.memory_store = MemoryStore(config=self.config)
        self.memory_retriever = MemoryRetriever(
            memory_store=self.memory_store, config=self.config
        )
        
        # 初始化 Agent
        from src.agent.action_executor import ActionExecutor
        from src.agent.reasoning import ReasoningEngine
        
        action_executor = ActionExecutor(
            retriever=self.rag_chain.retriever,
            generator=self.rag_chain.generator,
            tool_registry=self.tool_registry,
            config=self.config,
        )
        
        self.react_agent = ReActAgent(
            action_executor=action_executor,
            config=self.config,
        )

    def _register_tools(self):
        """注册工具"""
        try:
            if self.config.tools.bing_search.get("enabled", False):
                bing_tool = BingSearchTool(config=self.config)
                self.tool_registry.register_tool(bing_tool)
        except Exception as e:
            logger.warning(f"Bing 搜索工具注册失败: {e}")

        try:
            if self.config.tools.database.get("enabled", False):
                db_tool = DatabaseTool(config=self.config)
                self.tool_registry.register_tool(db_tool)
        except Exception as e:
            logger.warning(f"数据库工具注册失败: {e}")

    async def query(
        self,
        question: str,
        user_id: str = "default",
        use_agent: bool = False,
        enable_tool_fallback: bool = True,
        allow_general_knowledge: bool = False,
    ) -> dict:
        """
        执行查询

        Args:
            question: 问题
            user_id: 用户 ID
            use_agent: 是否使用 Agent 模式
            enable_tool_fallback: 是否启用工具回退（知识库无答案时调用工具）
            allow_general_knowledge: 是否允许使用通用知识（混合模式）

        Returns:
            查询结果字典
        """
        # 检索记忆
        memory_context = self.memory_retriever.retrieve_as_context(
            question, user_id, top_k=3
        )

        # 查询路由
        route_result = self.query_router.route(question, rag_chain=self.rag_chain)
        strategy = route_result["strategy"]

        # 根据策略执行查询
        if use_agent or strategy.get("use_agent", False):
            # 使用 ReAct Agent
            result = await self.react_agent.react_loop(
                query=question,
                memory_context=memory_context,
            )
        else:
            # 使用基础 RAG（支持工具回退和混合模式）
            result = self.rag_chain.query(
                question=question,
                additional_context=memory_context,
                return_sources=True,
                enable_tool_fallback=enable_tool_fallback,
                allow_general_knowledge=allow_general_knowledge,
            )
            
            if isinstance(result, str):
                result = {"answer": result, "sources": []}

        # 存储交互到记忆
        if isinstance(result, dict):
            answer = result.get("answer", "")
        else:
            answer = str(result)
            
        self.memory_store.store_interaction(
            user_id=user_id,
            query=question,
            answer=answer,
        )

        return {
            "question": question,
            "answer": answer,
            "sources": result.get("sources", []) if isinstance(result, dict) else [],
            "intent": route_result.get("intent"),
            "strategy": strategy,
        }

    def build_index(self, data_path: str, collection_name: str = "knowledge_base"):
        """
        构建索引

        Args:
            data_path: 数据路径（文件或目录）
            collection_name: 集合名称
        """
        logger.info(f"开始构建索引: {data_path}")

        # 加载文档
        loader = DocumentLoader()
        data_path_obj = Path(data_path)

        if data_path_obj.is_file():
            documents = loader.load_file(data_path)
        elif data_path_obj.is_dir():
            documents = loader.load_directory(data_path, recursive=True)
        else:
            raise ValueError(f"无效的数据路径: {data_path}")

        # 清理文档
        documents = loader.clean_documents(documents)

        # 分割文档
        splitter = TextSplitter(
            chunk_size=self.config.document.chunk_size,
            chunk_overlap=self.config.document.chunk_overlap,
        )
        chunks = splitter.split_documents(documents)

        # 创建索引
        index_manager = IndexManager(config=self.config)
        vectorstore = index_manager.create_index(
            documents=chunks,
            collection_name=collection_name,
            overwrite=True,
        )

        logger.info(f"索引构建完成: {collection_name}, 包含 {len(chunks)} 个块")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Agent-RAG 问答系统")
    parser.add_argument(
        "--mode",
        choices=["query", "build_index"],
        default="query",
        help="运行模式",
    )
    parser.add_argument("--question", type=str, help="查询问题")
    parser.add_argument("--data_path", type=str, help="数据路径（用于构建索引）")
    parser.add_argument("--user_id", type=str, default="default", help="用户 ID")
    parser.add_argument("--use_agent", action="store_true", help="使用 Agent 模式")
    parser.add_argument("--config", type=str, help="配置文件路径")

    args = parser.parse_args()

    # 初始化系统
    system = RAGSystem(config_path=args.config)

    if args.mode == "build_index":
        if not args.data_path:
            logger.error("构建索引需要指定 --data_path")
            return
        system.build_index(args.data_path)
        logger.info("索引构建完成")

    elif args.mode == "query":
        if not args.question:
            # 交互式查询
            logger.info("进入交互式查询模式（输入 'exit' 退出）")
            while True:
                question = input("\n请输入问题: ").strip()
                if question.lower() in ["exit", "quit", "退出"]:
                    break
                if not question:
                    continue

                result = await system.query(
                    question=question,
                    user_id=args.user_id,
                    use_agent=args.use_agent,
                    enable_tool_fallback=args.enable_tool,
                    allow_general_knowledge=args.allow_general_knowledge,
                )

                print(f"\n答案: {result['answer']}")
                if result.get("sources"):
                    print(f"\n来源: {', '.join(result['sources'][:3])}")
        else:
            # 单次查询
            result = await system.query(
                question=args.question,
                user_id=args.user_id,
                use_agent=args.use_agent,
                enable_tool_fallback=args.enable_tool,
                allow_general_knowledge=args.allow_general_knowledge,
            )

            print(f"\n问题: {result['question']}")
            print(f"答案: {result['answer']}")
            if result.get("sources"):
                print(f"\n来源: {', '.join(result['sources'][:3])}")


if __name__ == "__main__":
    asyncio.run(main())

