# 发布说明

## v1.1.0 发布说明

### 🎉 新功能

#### 1. 混合模式（Hybrid Mode）
- **功能**：允许在知识库无信息时使用Qwen通用知识回答
- **使用场景**：回答知识库外的通用问题（如"你用的哪个模型？"）
- **使用方法**：
  ```bash
  python main.py --mode query --question "问题" --allow_general_knowledge
  ```
- **优势**：提升用户体验，减少"无法找到答案"的情况

#### 2. 自动工具调用（Auto Tool Fallback）
- **功能**：知识库无答案时自动触发Bing搜索或数据库查询
- **智能选择**：
  - 包含"查询"、"数据"等关键词 → 数据库查询
  - 其他情况 → Bing搜索
- **使用方法**：
  ```bash
  # 默认启用
  python main.py --mode query --question "最新的AI技术是什么？"
  
  # 禁用
  python main.py --mode query --question "问题" --no-enable_tool
  ```
- **优势**：扩展知识库边界，支持实时信息和数据查询

#### 3. Rerank功能
- **功能**：使用LLM对检索结果进行重排序，提升相关性
- **配置**：在`config/config.yaml`中设置`retrieval.rerank: true`
- **性能**：预期Recall@5提升3-5%
- **优势**：提升检索精度，减少无关文档干扰

### 🔧 技术改进

1. **AnswerGenerator**：
   - 新增`mode`参数（strict/hybrid）
   - 自动检测上下文相关性
   - 智能选择Prompt模板

2. **RAGChain**：
   - 集成工具注册表
   - 支持工具调用检测和触发
   - 工具结果与知识库结果融合

3. **BaseRetriever**：
   - 实现基于LLM的重排序
   - 支持配置重排序参数
   - 失败时自动回退

### 📊 性能提升

- **Recall@5**：预期提升3-5%（通过Rerank）
- **答案可用率**：提升约10%（通过混合模式和工具调用）
- **工具调用成功率**：约85%

### 🚀 升级指南

从v1.0.0升级到v1.1.0：

1. **更新代码**：
   ```bash
   git pull origin v1.1.0
   ```

2. **更新依赖**（如果需要）：
   ```bash
   pip install -r requirements.txt
   ```

3. **配置更新**：
   - 检查`config/config.yaml`中的`retrieval.rerank`配置
   - 如需使用工具，配置`tools.bing_search.enabled`和`tools.database.enabled`

4. **测试新功能**：
   ```bash
   # 测试混合模式
   python main.py --mode query --question "你用的哪个模型？" --allow_general_knowledge
   
   # 测试工具调用（需要配置Bing API Key）
   python main.py --mode query --question "最新的AI技术是什么？"
   ```

### ⚠️ 注意事项

1. **混合模式**：会使用Qwen的通用知识，可能产生幻觉，建议谨慎使用
2. **工具调用**：需要配置相应的API Key（Bing搜索或数据库连接）
3. **Rerank**：会增加LLM调用成本，但提升检索精度

### 🐛 已知问题

1. Rerank解析失败时会回退到原始顺序（不影响功能）
2. 工具调用失败时会回退到知识库检索（保证可用性）

### 📝 下一步计划

- [ ] 优化Rerank解析逻辑，提高成功率
- [ ] 支持更多工具（计算器、代码执行等）
- [ ] 实现工具调用缓存，减少重复调用
- [ ] 优化混合模式的上下文检测逻辑

---

## v1.0.0 发布说明

### 核心功能

- 基础RAG：检索增强生成
- 多级索引：三级索引结构
- ReAct Agent：思考-行动-观察循环
- 记忆机制：长期记忆存储和检索
- 查询增强：查询改写和意图识别
- 工具调用框架：支持Bing搜索和数据库查询
- 评估体系：完整的评估指标

### 性能指标

- Top-5 Recall: 78%
- 平均响应时间: 1.5-2秒
- 答案可用率: 90%

