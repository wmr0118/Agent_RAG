#!/bin/bash
# Git仓库准备脚本 - 用于发布v1.0.0

echo "=========================================="
echo "准备Git仓库并发布v1.0.0"
echo "=========================================="
echo ""

# 检查是否已有git仓库
if [ -d ".git" ]; then
    echo "Git仓库已存在"
else
    echo "初始化Git仓库..."
    git init
fi

# 添加所有文件
echo "添加文件到Git..."
git add .

# 提交
echo "提交代码..."
git commit -m "Initial commit: v1.0.0 - Agent-RAG系统基础版本

- 基础RAG功能：检索增强生成
- 多级索引：三级索引结构
- ReAct Agent：思考-行动-观察循环
- 记忆机制：长期记忆存储和检索
- 查询增强：查询改写和意图识别
- 工具调用框架：支持Bing搜索和数据库查询
- 评估体系：完整的评估指标
- 测试知识库：10份文档，25条测试用例"

# 创建tag
echo "创建v1.0.0 tag..."
git tag -a v1.0.0 -m "Release v1.0.0: Agent-RAG系统基础版本"

echo ""
echo "=========================================="
echo "✅ Git仓库准备完成！"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 在GitHub上创建新仓库"
echo "2. 添加远程仓库: git remote add origin <your-repo-url>"
echo "3. 推送代码: git push -u origin main"
echo "4. 推送tag: git push origin v1.0.0"
echo ""

