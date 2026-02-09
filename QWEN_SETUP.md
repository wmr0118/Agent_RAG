# Qwen 模型配置指南

## 为什么使用 Qwen？

对于国内用户，使用 Qwen（通义千问）模型有以下优势：

1. **访问速度快**：无需翻墙，API 响应更快
2. **成本更低**：国内模型服务通常价格更优惠
3. **中文支持好**：对中文理解和生成能力更强
4. **数据合规**：数据完全在国内处理，符合数据安全要求

## 快速开始

### 1. 安装依赖

```bash
conda activate rag
pip install dashscope
```

### 2. 获取 API Key

访问 [阿里云 DashScope 控制台](https://dashscope.console.aliyun.com/) 获取 API Key。

### 3. 配置环境变量

创建 `.env` 文件或设置环境变量：

```bash
export DASHSCOPE_API_KEY="your_dashscope_api_key_here"
```

### 4. 更新配置文件

编辑 `config/config.yaml`：

```yaml
# LLM 配置
llm:
  provider: "qwen"  # 改为 "qwen"
  model_name: "qwen-turbo"  # 可选: qwen-turbo, qwen-plus, qwen-max
  temperature: 0.7
  max_tokens: 2000
  api_key: "${DASHSCOPE_API_KEY}"  # 使用 DASHSCOPE_API_KEY

# Embedding 配置（可选，也切换到 Qwen）
embedding:
  provider: "dashscope"  # 改为 "dashscope"
  model_name: "text-embedding-v2"  # Qwen 的 embedding 模型
  batch_size: 100
  dimension: 1536
```

### 5. 可用的 Qwen 模型

#### Chat 模型（LLM）
- `qwen-turbo`: 快速响应，适合简单任务
- `qwen-plus`: 平衡性能和速度
- `qwen-max`: 最强性能，适合复杂任务

#### Embedding 模型
- `text-embedding-v2`: Qwen 的文本嵌入模型

## 切换回 OpenAI

如果需要切换回 OpenAI，只需修改配置：

```yaml
llm:
  provider: "openai"
  model_name: "gpt-4"
  api_key: "${OPENAI_API_KEY}"

embedding:
  provider: "openai"
  model_name: "text-embedding-3-small"
```

## 验证配置

运行测试命令：

```bash
python main.py --mode query --question "测试问题"
```

如果看到正常输出，说明配置成功！

## 注意事项

1. **API Key 安全**：不要将 API Key 提交到 Git 仓库
2. **模型选择**：根据任务复杂度选择合适的模型
3. **成本控制**：注意 API 调用费用，建议设置使用限额
4. **网络要求**：Qwen 需要能访问阿里云服务

## 常见问题

### Q: 如何查看 API 使用情况？
A: 登录 [DashScope 控制台](https://dashscope.console.aliyun.com/) 查看使用统计。

### Q: 支持流式输出吗？
A: 是的，Qwen 支持流式输出，代码已自动支持。

### Q: 可以同时使用 OpenAI 和 Qwen 吗？
A: 可以，但需要在代码中分别配置不同的实例。当前实现是全局切换。

### Q: Embedding 也必须用 Qwen 吗？
A: 不是必须的，可以 LLM 用 Qwen，Embedding 用 OpenAI，或反之。

