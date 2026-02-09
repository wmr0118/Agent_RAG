#!/bin/bash
# 安装依赖脚本

echo "=========================================="
echo "Agent-RAG 系统依赖安装"
echo "=========================================="
echo ""

# 检查Python版本
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "Python版本: $python_version"
echo ""

# 检查pip
if ! command -v pip &> /dev/null; then
    echo "错误: pip未安装，请先安装pip"
    exit 1
fi

echo "开始安装依赖包..."
echo ""

# 安装依赖
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ 依赖安装完成！"
    echo "=========================================="
    echo ""
    echo "下一步："
    echo "1. 配置环境变量（运行 python setup_env.py）"
    echo "2. 构建索引（运行 python main.py --mode build_index --data_path data/raw/）"
    echo "3. 测试查询（运行 python main.py --mode query --question '如何创建用户？'）"
else
    echo ""
    echo "=========================================="
    echo "❌ 依赖安装失败"
    echo "=========================================="
    echo ""
    echo "请检查："
    echo "1. 网络连接是否正常"
    echo "2. pip是否可用"
    echo "3. 是否需要使用代理或镜像源"
    echo ""
    echo "如果使用国内网络，可以尝试使用清华镜像："
    echo "pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple"
fi

