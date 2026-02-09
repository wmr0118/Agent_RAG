# 故障排除指南

## 问题1: ModuleNotFoundError - 缺少依赖包

### 错误信息
```
ModuleNotFoundError: No module named 'pydantic'
ModuleNotFoundError: No module named 'langchain'
```

### 原因
Python环境中缺少必要的依赖包。

### 解决方法

#### 方法1: 使用安装脚本（推荐）
```bash
# 给脚本添加执行权限（如果还没有）
chmod +x install_deps.sh

# 运行安装脚本
./install_deps.sh
```

#### 方法2: 手动安装
```bash
# 直接安装
pip install -r requirements.txt

# 如果网络较慢，使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### 方法3: 使用虚拟环境（推荐用于生产环境）
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate
# Windows:
# venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 验证安装
```bash
python -c "import pydantic; import langchain; print('依赖安装成功')"
```

---

## 问题2: 环境变量未配置

### 错误信息
```
KeyError: 'DASHSCOPE_API_KEY'
或
API调用失败
```

### 原因
缺少API密钥配置。

### 解决方法

#### 方法1: 使用快速设置脚本
```bash
python setup_env.py
```

#### 方法2: 手动创建.env文件
```bash
# 创建.env文件
cat > .env << EOF
DASHSCOPE_API_KEY=your_api_key_here
EOF
```

#### 方法3: 设置环境变量
```bash
# macOS/Linux
export DASHSCOPE_API_KEY=your_api_key_here

# Windows
set DASHSCOPE_API_KEY=your_api_key_here
```

### 验证配置
```bash
# 检查.env文件是否存在
ls -la .env

# 检查环境变量（如果使用export）
echo $DASHSCOPE_API_KEY
```

---

## 问题3: 构建索引失败

### 错误信息
```
FileNotFoundError: 文件不存在: data/raw/...
或
ValueError: 无效的数据路径
```

### 原因
- 数据路径不正确
- 文档文件不存在

### 解决方法

#### 检查数据路径
```bash
# 检查目录结构
ls -la data/raw/

# 应该看到类似结构：
# 01-产品介绍/
# 02-快速开始/
# 03-功能指南/
# ...
```

#### 使用正确的路径构建索引
```bash
# 构建整个目录
python main.py --mode build_index --data_path data/raw/

# 或构建单个文件
python main.py --mode build_index --data_path data/raw/01-产品介绍/01-产品概述.md
```

#### 检查文档格式
确保文档是Markdown格式（.md），且文件编码为UTF-8。

---

## 问题4: 查询失败

### 错误信息
```
未找到相关信息
或
索引不存在
```

### 原因
- 索引未构建
- 索引路径配置错误

### 解决方法

#### 步骤1: 检查索引是否存在
```bash
# 检查索引目录
ls -la data/chroma_db/

# 应该看到chroma.sqlite3文件
```

#### 步骤2: 重新构建索引
```bash
python main.py --mode build_index --data_path data/raw/
```

#### 步骤3: 检查配置文件
检查 `config/config.yaml` 中的向量数据库配置：
```yaml
vector_db:
  persist_directory: "./data/chroma_db"
  collection_name: "knowledge_base"
```

---

## 问题5: API调用失败

### 错误信息
```
API调用失败
或
401 Unauthorized
```

### 原因
- API密钥错误或过期
- API密钥未正确配置
- 网络连接问题

### 解决方法

#### 检查API密钥
```bash
# 检查.env文件
cat .env

# 应该包含：
# DASHSCOPE_API_KEY=sk-...
```

#### 测试API连接
```python
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('DASHSCOPE_API_KEY')
print(f"API Key: {api_key[:10]}..." if api_key else "API Key not found")
```

#### 获取新的API密钥
- Qwen: https://dashscope.console.aliyun.com/
- OpenAI: https://platform.openai.com/api-keys

---

## 问题6: 权限错误

### 错误信息
```
PermissionError: Operation not permitted
```

### 原因
- 文件权限问题
- 目录不可写

### 解决方法

#### 检查目录权限
```bash
# 检查data目录权限
ls -ld data/

# 如果需要，修改权限
chmod -R 755 data/
```

#### 检查写入权限
```bash
# 测试写入权限
touch data/test_write.txt && rm data/test_write.txt
```

---

## 快速诊断脚本

运行以下命令进行完整诊断：

```bash
#!/bin/bash
echo "=== 环境检查 ==="
python --version
echo ""

echo "=== 依赖检查 ==="
python -c "import pydantic; print('✓ pydantic')" 2>&1 || echo "✗ pydantic 未安装"
python -c "import langchain; print('✓ langchain')" 2>&1 || echo "✗ langchain 未安装"
python -c "import chromadb; print('✓ chromadb')" 2>&1 || echo "✗ chromadb 未安装"
echo ""

echo "=== 配置文件检查 ==="
[ -f ".env" ] && echo "✓ .env 文件存在" || echo "✗ .env 文件不存在"
[ -f "config/config.yaml" ] && echo "✓ config.yaml 存在" || echo "✗ config.yaml 不存在"
echo ""

echo "=== 数据文件检查 ==="
[ -d "data/raw" ] && echo "✓ data/raw 目录存在" || echo "✗ data/raw 目录不存在"
[ -f "data/chroma_db/chroma.sqlite3" ] && echo "✓ 索引已构建" || echo "✗ 索引未构建"
echo ""

echo "=== 检查完成 ==="
```

---

## 常见问题FAQ

### Q: 为什么pip install很慢？
A: 可以使用国内镜像源加速：
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q: 如何确认所有依赖都已安装？
A: 运行：
```bash
pip list | grep -E "(pydantic|langchain|chromadb|dashscope)"
```

### Q: 构建索引需要多长时间？
A: 对于10份文档（约600条知识单元），通常需要2-5分钟，取决于：
- 文档数量
- 网络速度（下载embedding模型）
- 计算机性能

### Q: 索引构建后在哪里？
A: 索引存储在 `data/chroma_db/` 目录下，包括：
- `chroma.sqlite3`: 数据库文件
- `index_metadata.json`: 索引元数据

### Q: 如何删除旧索引重新构建？
A: 
```bash
# 删除旧索引
rm -rf data/chroma_db/*

# 重新构建
python main.py --mode build_index --data_path data/raw/
```

---

## 获取帮助

如果以上方法都无法解决问题，请：

1. 检查错误日志的完整输出
2. 确认Python版本（需要Python 3.8+）
3. 确认所有依赖都已正确安装
4. 检查网络连接和API密钥配置

