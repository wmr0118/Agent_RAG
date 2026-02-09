#!/usr/bin/env python3
"""环境检查脚本"""
import sys
import os
from pathlib import Path

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    print(f"✓ Python版本: {version.major}.{version.minor}.{version.micro}")
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("  ⚠️  警告: 需要Python 3.8+")
        return False
    return True

def check_dependencies():
    """检查依赖包"""
    required_packages = [
        'pydantic',
        'langchain',
        'langchain_chroma',
        'langchain_community',
        'chromadb',
        'dashscope',
        'yaml',
        'dotenv',
    ]
    
    missing = []
    for package in required_packages:
        try:
            if package == 'yaml':
                __import__('yaml')
            elif package == 'dotenv':
                __import__('dotenv')
            else:
                __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} 未安装")
            missing.append(package)
    
    return len(missing) == 0, missing

def check_config_files():
    """检查配置文件"""
    config_files = {
        '.env': '环境变量文件',
        'config/config.yaml': '配置文件',
    }
    
    all_exist = True
    for file_path, desc in config_files.items():
        if Path(file_path).exists():
            print(f"✓ {desc}: {file_path}")
        else:
            print(f"✗ {desc}: {file_path} 不存在")
            all_exist = False
    
    return all_exist

def check_data_files():
    """检查数据文件"""
    data_dir = Path('data/raw')
    if data_dir.exists():
        md_files = list(data_dir.rglob('*.md'))
        print(f"✓ 数据目录存在: {data_dir}")
        print(f"  - 找到 {len(md_files)} 个Markdown文件")
        return True
    else:
        print(f"✗ 数据目录不存在: {data_dir}")
        return False

def check_index():
    """检查索引"""
    index_dir = Path('data/chroma_db')
    if index_dir.exists():
        sqlite_file = index_dir / 'chroma.sqlite3'
        if sqlite_file.exists():
            print(f"✓ 索引已构建: {sqlite_file}")
            return True
        else:
            print(f"⚠ 索引目录存在但未构建索引")
            return False
    else:
        print(f"⚠ 索引目录不存在，需要构建索引")
        return False

def main():
    print("=" * 60)
    print("Agent-RAG 系统环境检查")
    print("=" * 60)
    print()
    
    all_ok = True
    
    print("1. Python环境检查")
    print("-" * 60)
    if not check_python_version():
        all_ok = False
    print()
    
    print("2. 依赖包检查")
    print("-" * 60)
    deps_ok, missing = check_dependencies()
    if not deps_ok:
        all_ok = False
        print(f"\n缺少以下依赖包: {', '.join(missing)}")
        print("请运行: pip install -r requirements.txt")
    print()
    
    print("3. 配置文件检查")
    print("-" * 60)
    if not check_config_files():
        all_ok = False
        print("\n请运行: python setup_env.py 配置环境变量")
    print()
    
    print("4. 数据文件检查")
    print("-" * 60)
    if not check_data_files():
        all_ok = False
    print()
    
    print("5. 索引检查")
    print("-" * 60)
    check_index()
    print()
    
    print("=" * 60)
    if all_ok:
        print("✅ 环境检查通过！")
        print("\n下一步:")
        if not Path('data/chroma_db/chroma.sqlite3').exists():
            print("1. 构建索引: python main.py --mode build_index --data_path data/raw/")
        print("2. 测试查询: python main.py --mode query --question '如何创建用户？'")
    else:
        print("❌ 环境检查未通过，请根据上述提示修复问题")
        print("\n快速修复:")
        if missing:
            print(f"1. 安装依赖: pip install -r requirements.txt")
        if not Path('.env').exists():
            print("2. 配置环境: python setup_env.py")
    print("=" * 60)

if __name__ == '__main__':
    main()

