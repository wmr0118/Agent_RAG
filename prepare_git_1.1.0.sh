#!/bin/bash
# Git仓库准备脚本 - 用于发布v1.1.0

echo "=========================================="
echo "准备Git仓库并发布v1.1.0"
echo "=========================================="
echo ""

# 检查是否已有git仓库
if [ ! -d ".git" ]; then
    echo "错误: Git仓库不存在，请先运行 prepare_git.sh 创建v1.0.0"
    exit 1
fi

# 检查当前分支
current_branch=$(git branch --show-current)
echo "当前分支: $current_branch"

# 创建新分支（如果不在新分支上）
if [ "$current_branch" != "v1.1.0" ]; then
    echo "创建新分支 v1.1.0..."
    git checkout -b v1.1.0
fi

# 添加所有文件
echo "添加文件到Git..."
git add .

# 提交
echo "提交代码..."
git commit -m "Release v1.1.0: 混合模式、自动工具调用、Rerank功能

新增功能：
- 混合模式：支持知识库+通用知识混合回答
- 自动工具调用：知识库无答案时自动触发Bing搜索或数据库查询
- Rerank功能：实现两阶段检索+重排序

技术改进：
- AnswerGenerator支持严格模式和混合模式
- RAGChain集成工具调用能力
- BaseRetriever实现基于LLM的重排序
- 优化工具选择和错误处理"

# 创建tag
echo "创建v1.1.0 tag..."
git tag -a v1.1.0 -m "Release v1.1.0: 混合模式、自动工具调用、Rerank功能"

echo ""
echo "=========================================="
echo "✅ v1.1.0版本准备完成！"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 推送到GitHub: git push origin v1.1.0"
echo "2. 推送tag: git push origin v1.1.0"
echo "3. 如果需要合并到main: git checkout main && git merge v1.1.0"
echo ""

