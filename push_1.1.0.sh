#!/bin/bash
# 推送v1.1.0版本到GitHub

echo "=========================================="
echo "推送v1.1.0版本到GitHub"
echo "=========================================="
echo ""

# 检查是否在v1.1.0分支
current_branch=$(git branch --show-current)
if [ "$current_branch" != "v1.1.0" ]; then
    echo "⚠️  当前不在v1.1.0分支，切换到v1.1.0分支..."
    git checkout v1.1.0
fi

# 检查远程仓库
if ! git remote | grep -q "^origin$"; then
    echo "错误: 未配置远程仓库origin"
    echo "请先运行: git remote add origin <your-repo-url>"
    exit 1
fi

echo "1. 推送分支 v1.1.0..."
git push origin refs/heads/v1.1.0:refs/heads/v1.1.0

if [ $? -eq 0 ]; then
    echo "✅ 分支推送成功"
else
    echo "❌ 分支推送失败"
    exit 1
fi

echo ""
echo "2. 推送tag v1.1.0..."
git push origin refs/tags/v1.1.0

if [ $? -eq 0 ]; then
    echo "✅ Tag推送成功"
else
    echo "❌ Tag推送失败"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ v1.1.0版本推送完成！"
echo "=========================================="
echo ""
echo "可以在GitHub上查看："
echo "  - 分支: https://github.com/wmr0118/Agent_RAG/tree/v1.1.0"
echo "  - Tag: https://github.com/wmr0118/Agent_RAG/releases/tag/v1.1.0"
echo ""

