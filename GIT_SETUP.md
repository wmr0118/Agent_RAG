# Git仓库设置指南

## 发布v1.0.0版本

### 步骤1: 初始化Git仓库并提交v1.0.0

```bash
# 运行准备脚本
./prepare_git.sh

# 或者手动执行：
git init
git add .
git commit -m "Initial commit: v1.0.0 - Agent-RAG系统基础版本"
git tag -a v1.0.0 -m "Release v1.0.0: Agent-RAG系统基础版本"
```

### 步骤2: 在GitHub上创建仓库

1. 登录GitHub
2. 点击"New repository"
3. 填写仓库名称（如：agent-rag-system）
4. 选择Public或Private
5. **不要**初始化README、.gitignore或license（我们已经有了）

### 步骤3: 连接远程仓库并推送

```bash
# 添加远程仓库（替换为你的仓库URL）
git remote add origin https://github.com/your-username/agent-rag-system.git

# 推送到main分支
git push -u origin main

# 推送tag
git push origin v1.0.0
```

---

## 发布v1.1.0版本

### 步骤1: 创建新分支并提交v1.1.0

```bash
# 运行准备脚本
./prepare_git_1.1.0.sh

# 或者手动执行：
git checkout -b v1.1.0
git add .
git commit -m "Release v1.1.0: 混合模式、自动工具调用、Rerank功能"
git tag -a v1.1.0 -m "Release v1.1.0: 混合模式、自动工具调用、Rerank功能"
```

### 步骤2: 推送到GitHub

```bash
# 推送分支
git push -u origin v1.1.0

# 推送tag
git push origin v1.1.0

# 如果需要合并到main
git checkout main
git merge v1.1.0
git push origin main
```

---

## 版本管理建议

### 分支策略

- **main**: 稳定版本，只包含已测试的功能
- **v1.1.0**: 功能分支，用于开发新功能
- **develop**: 开发分支（可选）

### Tag命名

- 使用语义化版本：`v1.0.0`, `v1.1.0`, `v2.0.0`
- Tag消息包含版本说明

### 提交信息规范

```
类型: 简短描述

详细说明（可选）

- 功能1
- 功能2
```

类型：
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `refactor`: 重构
- `test`: 测试

---

## 常见问题

### Q: 如何回退到v1.0.0？

```bash
git checkout v1.0.0
```

### Q: 如何查看所有tag？

```bash
git tag -l
```

### Q: 如何删除本地tag？

```bash
git tag -d v1.1.0
```

### Q: 如何删除远程tag？

```bash
git push origin --delete v1.1.0
```

---

## GitHub Release创建

发布tag后，可以在GitHub上创建Release：

1. 进入仓库页面
2. 点击"Releases" → "Create a new release"
3. 选择tag（v1.0.0或v1.1.0）
4. 填写Release标题和说明
5. 可以上传附件（如打包的代码）
6. 点击"Publish release"

Release说明可以参考`CHANGELOG.md`和`RELEASE_NOTES.md`。

