import sys
import os
import asyncio
from cleanmd import process_markdown
import logging
from pathlib import Path
import argparse
from typing import List, Optional

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(message)s")


async def main():
    """
    主程序入口
    1. 如果命令行参数提供了文件路径，直接处理该文件
    2. 如果没有提供参数，提示用户输入文件路径
    3. 直接开始处理文件
    """
    # 获取文件路径
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        print("\n欢迎使用 Cleanmd - Markdown文件清理工具")
        print("=" * 50)
        input_file = input("请输入要处理的Markdown文件路径: ").strip()

    # 验证文件
    if not input_file:
        print("错误：未提供文件路径")
        return 1

    if not input_file.endswith(".md"):
        print("错误：文件必须是Markdown格式（.md结尾）")
        return 1

    if not os.path.exists(input_file):
        print(f"错误：找不到文件 '{input_file}'")
        return 1

    # 开始处理文件
    print("\n开始处理文件...")
    print("=" * 50)
    return await process_markdown(input_file)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
