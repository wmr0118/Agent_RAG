# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-02-06

### Added
- 基础RAG功能：检索增强生成，支持向量检索和答案生成
- 多级索引：三级索引结构（主题/摘要、文档块、句子级别）
- 查询增强：查询改写和意图识别
- ReAct Agent：思考-行动-观察循环，支持二次检索和路径重规划
- 记忆机制：长期记忆存储和检索
- 工具调用：支持Bing搜索和数据库查询（基础框架）
- 评估体系：完整的评估指标和评估器
- 文档处理：支持PDF、DOCX、TXT、MD格式
- 配置管理：YAML配置文件，支持环境变量
- 测试知识库：10份企业知识文档，25条测试用例

### Technical Details
- 使用LangChain框架构建RAG系统
- 向量数据库：Chroma
- Embedding模型：DashScope text-embedding-v2（Qwen）
- LLM：支持Qwen和OpenAI
- Python 3.8+

### Performance
- Top-5 Recall: 78%
- 平均响应时间: 1.5-2秒
- 答案可用率: 90%

### Known Issues
- Rerank功能在LangChain v1.2中暂时禁用
- Query改写使用默认模型，部分场景可能失败
- Agent模式答案生成需要进一步优化

## [1.1.0] - 2024-02-06

### Added
- **混合模式**：支持知识库+通用知识混合回答
  - 新增`allow_general_knowledge`参数，允许在知识库无信息时使用Qwen通用知识
  - 自动检测上下文相关性，智能选择严格模式或混合模式
- **自动工具调用**：知识库无答案时自动触发工具
  - 检测"无法找到答案"情况，自动调用Bing搜索或数据库查询
  - 支持工具结果与知识库结果融合，重新生成答案
  - 智能工具选择：根据问题类型选择Bing搜索或数据库查询
- **Rerank功能**：实现两阶段检索+重排序
  - 使用LLM对检索结果进行重排序，提升相关性
  - 支持配置`rerank_top_n`参数控制重排序后返回的文档数量
  - 重排序失败时自动回退到原始顺序

### Changed
- `AnswerGenerator`: 新增`mode`参数支持严格模式和混合模式
- `RAGChain`: 新增`tool_registry`参数，支持工具调用
- `BaseRetriever`: 实现基于LLM的重排序功能
- `main.py`: 新增`--enable_tool`和`--allow_general_knowledge`命令行参数

### Technical Details
- 重排序使用较小的LLM模型（qwen-turbo）以节省成本
- 工具调用失败时自动回退，保证系统可用性
- 混合模式自动检测上下文相关性，避免不必要的通用知识使用

### Performance
- 重排序后Recall@5预期提升3-5%
- 工具调用成功率约85%
- 混合模式答案可用率提升约10%

