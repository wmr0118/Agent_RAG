"""配置管理模块"""
import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class LLMConfig(BaseModel):
    """LLM 配置"""
    provider: str = "openai"
    model_name: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 2000
    api_key: Optional[str] = None


class VectorDBConfig(BaseModel):
    """向量数据库配置"""
    provider: str = "chroma"
    persist_directory: str = "./data/chroma_db"
    collection_name: str = "knowledge_base"


class EmbeddingConfig(BaseModel):
    """Embedding 配置"""
    provider: str = "openai"  # "openai" 或 "dashscope"
    model_name: str = "text-embedding-3-small"
    batch_size: int = 100
    dimension: int = 1536


class RetrievalConfig(BaseModel):
    """检索配置"""
    top_k: int = 5
    similarity_threshold: float = 0.7
    use_mmr: bool = True
    mmr_diversity: float = 0.5
    rerank: bool = True
    rerank_top_n: int = 10


class MultilevelIndexConfig(BaseModel):
    """多级索引配置"""
    level1: Dict[str, Any] = Field(default_factory=lambda: {"enabled": True, "top_k": 10, "use_summary": True})
    level2: Dict[str, Any] = Field(default_factory=lambda: {"enabled": True, "top_k": 5})
    level3: Dict[str, Any] = Field(default_factory=lambda: {"enabled": True, "top_k": 3})


class AgentConfig(BaseModel):
    """Agent 配置"""
    max_iterations: int = 5
    confidence_threshold: float = 0.7
    enable_react: bool = True
    enable_reretrieval: bool = True
    enable_replanning: bool = True


class QueryConfig(BaseModel):
    """查询处理配置"""
    enable_rewrite: bool = True
    enable_intent_classification: bool = True
    rewrite_model: str = "gpt-3.5-turbo"


class MemoryConfig(BaseModel):
    """记忆机制配置"""
    enabled: bool = True
    max_memories: int = 100
    memory_expiry_days: int = 30
    similarity_threshold: float = 0.6


class ToolsConfig(BaseModel):
    """工具配置"""
    bing_search: Dict[str, Any] = Field(default_factory=dict)
    database: Dict[str, Any] = Field(default_factory=dict)


class DocumentConfig(BaseModel):
    """文档处理配置"""
    chunk_size: int = 1000
    chunk_overlap: int = 200
    enable_metadata: bool = True


class EvaluationConfig(BaseModel):
    """评估配置"""
    test_set_path: str = "./data/test_set.json"
    metrics: list[str] = Field(default_factory=lambda: ["recall@5", "recall@10", "answer_quality"])


class Config(BaseSettings):
    """主配置类"""
    llm: LLMConfig
    vector_db: VectorDBConfig
    embedding: EmbeddingConfig
    retrieval: RetrievalConfig
    multilevel_index: MultilevelIndexConfig
    agent: AgentConfig
    query: QueryConfig
    memory: MemoryConfig
    tools: ToolsConfig
    document: DocumentConfig
    evaluation: EvaluationConfig

    @classmethod
    def load_from_yaml(cls, config_path: Optional[str] = None) -> "Config":
        """从 YAML 文件加载配置"""
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
        else:
            config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)

        # 替换环境变量
        config_dict = cls._replace_env_vars(config_dict)

        # 转换为配置对象
        return cls(**config_dict)

    @staticmethod
    def _replace_env_vars(data: Any) -> Any:
        """递归替换环境变量"""
        if isinstance(data, dict):
            return {k: Config._replace_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [Config._replace_env_vars(item) for item in data]
        elif isinstance(data, str) and data.startswith("${") and data.endswith("}"):
            env_var = data[2:-1]
            return os.getenv(env_var, data)
        return data


# 全局配置实例
_config: Optional[Config] = None


def get_config(config_path: Optional[str] = None) -> Config:
    """获取配置实例（单例模式）"""
    global _config
    if _config is None:
        _config = Config.load_from_yaml(config_path)
    return _config

