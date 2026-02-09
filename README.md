# Agent-RAG 问答系统

基于 RAG + ReAct Agent 的智能问答系统，支持多源知识库检索、工具调用与多轮推理。

**当前版本**: v1.1.0

## 版本历史

- **v1.0.0** (2024-02-06): 初始版本，包含基础RAG、多级索引、ReAct Agent、记忆机制等核心功能
- **v1.1.0** (2024-02-06): 新增混合模式、自动工具调用、Rerank功能

详细变更请查看 [CHANGELOG.md](CHANGELOG.md)

## v1.1.0 新功能

### 混合模式
允许在知识库无信息时使用Qwen通用知识回答：
```bash
python main.py --mode query --question "你用的哪个模型？" --allow_general_knowledge
```

### 自动工具调用
知识库无答案时自动触发Bing搜索或数据库查询：
```bash
# 默认启用工具回退
python main.py --mode query --question "最新的AI技术是什么？"

# 禁用工具回退
python main.py --mode query --question "问题" --no-enable_tool
```

### Rerank功能
使用LLM对检索结果进行重排序，提升相关性（在config.yaml中配置）

## 功能特性

- **基础 RAG**: 检索增强生成，支持向量检索和答案生成
- **多级索引**: 三级索引结构（主题/摘要、文档块、句子级别）
- **查询增强**: 查询改写和意图识别
- **ReAct Agent**: 思考-行动-观察循环，支持二次检索和路径重规划
- **记忆机制**: 长期记忆存储和检索
- **工具调用**: 支持 Bing 搜索和数据库查询
- **评估体系**: 完整的评估指标和评估器

## 项目结构

```
rag/
├── src/
│   ├── core/                    # 核心 RAG 组件
│   ├── indexing/               # 索引相关
│   ├── query/                  # 查询处理
│   ├── agent/                  # Agent 相关
│   ├── memory/                 # 记忆机制
│   ├── tools/                  # 工具调用
│   ├── utils/                  # 工具函数
│   └── evaluation/             # 评估模块
├── data/                       # 数据目录
├── config/                     # 配置文件
├── tests/                      # 测试文件
├── requirements.txt
├── README.md
└── main.py                     # 主入口
```

## 安装

1. 克隆仓库
```bash
git clone <repository-url>
cd rag
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境变量

**方法 1：使用快速设置脚本（推荐）**
```bash
python setup_env.py
```

**方法 2：手动创建 `.env` 文件**

使用 Qwen（国内推荐）：
```bash
DASHSCOPE_API_KEY=your_dashscope_api_key
```

使用 OpenAI（国际）：
```bash
OPENAI_API_KEY=your_openai_api_key
```

其他可选配置：
```bash
BING_API_KEY=your_bing_api_key  # 可选
DATABASE_URL=your_database_url   # 可选
```

**获取 API Key：**
- Qwen: https://dashscope.console.aliyun.com/
- OpenAI: https://platform.openai.com/api-keys

4. 配置系统
编辑 `config/config.yaml`，设置相关参数。

**使用 Qwen 模型（国内推荐）：**
- 设置 `llm.provider: "qwen"`
- 设置 `llm.model_name: "qwen-turbo"` 或 `qwen-plus`、`qwen-max`
- 详细配置请参考 [QWEN_SETUP.md](QWEN_SETUP.md)

## 使用方法

### 1. 构建索引

```bash
python main.py --mode build_index --data_path ./data/raw
```

### 2. 查询

交互式查询：
```bash
python main.py --mode query
```

单次查询：
```bash
python main.py --mode query --question "什么是RAG？"
```

使用 Agent 模式：
```bash
python main.py --mode query --question "什么是RAG？" --use_agent
```

### 3. 评估

```python
from src.evaluation.evaluator import Evaluator
from src.core.rag_chain import RAGChain
from src.utils.config import get_config

config = get_config()
rag_chain = RAGChain(config=config)
evaluator = Evaluator(rag_chain=rag_chain, config=config)

test_set = evaluator.load_test_set()
results = evaluator.evaluate(test_set)
print(results)
```

## 配置说明

主要配置项（`config/config.yaml`）：

- **LLM**: OpenAI API 配置
- **向量数据库**: Chroma 配置
- **检索参数**: top_k, similarity_threshold 等
- **Agent 参数**: max_iterations, confidence_threshold 等
- **工具配置**: Bing 搜索、数据库连接等

## 核心模块

### 1. 基础 RAG (`src/core/`)
- `retriever.py`: 向量检索器
- `generator.py`: 答案生成器
- `rag_chain.py`: RAG 链组装

### 2. 多级索引 (`src/indexing/`)
- `multilevel_index.py`: 三级索引实现
- `index_manager.py`: 索引生命周期管理

### 3. 查询处理 (`src/query/`)
- `query_rewriter.py`: 查询改写
- `intent_classifier.py`: 意图分类
- `query_router.py`: 查询路由

### 4. ReAct Agent (`src/agent/`)
- `react_agent.py`: ReAct 循环实现
- `reasoning.py`: 推理逻辑
- `action_executor.py`: 动作执行器

### 5. 记忆机制 (`src/memory/`)
- `memory_store.py`: 记忆存储
- `memory_retriever.py`: 记忆检索

### 6. 工具调用 (`src/tools/`)
- `tool_registry.py`: 工具注册表
- `search_tool.py`: Bing 搜索工具
- `db_tool.py`: 数据库查询工具

## 技术栈

- **LangChain**: RAG 框架
- **OpenAI**: LLM 和 Embedding
- **Chroma**: 向量数据库
- **Python 3.8+**

## 评估指标

系统支持以下评估指标：

- **检索指标**: Recall@K, Precision@K, MRR
- **生成指标**: 答案质量、事实准确性、一致性
- **系统指标**: 响应时间、吞吐量

## 开发

运行测试：
```bash
pytest tests/
```

代码格式化：
```bash
black src/
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

