#!/usr/bin/env python3
"""快速设置环境变量脚本"""
import os
from pathlib import Path

def setup_env():
    """设置环境变量"""
    env_file = Path(".env")
    
    print("=" * 60)
    print("Agent-RAG 系统环境配置")
    print("=" * 60)
    print()
    
    # 检查是否已有 .env 文件
    if env_file.exists():
        print("⚠️  发现已存在的 .env 文件")
        response = input("是否覆盖？(y/N): ").strip().lower()
        if response != 'y':
            print("取消操作")
            return
    
    print("请选择 LLM 提供商：")
    print("1. Qwen (通义千问) - 国内推荐")
    print("2. OpenAI")
    choice = input("请选择 (1/2，默认1): ").strip() or "1"
    
    env_content = []
    
    if choice == "1":
        print("\n使用 Qwen 模型")
        print("获取 API Key: https://dashscope.console.aliyun.com/")
        api_key = input("请输入 DASHSCOPE_API_KEY: ").strip()
        if api_key:
            env_content.append(f"DASHSCOPE_API_KEY={api_key}")
        else:
            print("⚠️  未输入 API Key，请稍后手动设置")
    else:
        print("\n使用 OpenAI 模型")
        print("获取 API Key: https://platform.openai.com/api-keys")
        api_key = input("请输入 OPENAI_API_KEY: ").strip()
        if api_key:
            env_content.append(f"OPENAI_API_KEY={api_key}")
        else:
            print("⚠️  未输入 API Key，请稍后手动设置")
    
    # 可选配置
    print("\n可选配置（直接回车跳过）：")
    bing_key = input("BING_API_KEY (可选): ").strip()
    if bing_key:
        env_content.append(f"BING_API_KEY={bing_key}")
    
    db_url = input("DATABASE_URL (可选): ").strip()
    if db_url:
        env_content.append(f"DATABASE_URL={db_url}")
    
    # 写入文件
    if env_content:
        with open(env_file, "w") as f:
            f.write("\n".join(env_content) + "\n")
        print(f"\n✅ 环境变量已保存到 {env_file}")
        print("\n提示：.env 文件已添加到 .gitignore，不会被提交到 Git")
    else:
        print("\n⚠️  未设置任何环境变量")
        print("请手动创建 .env 文件或设置环境变量")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    setup_env()

