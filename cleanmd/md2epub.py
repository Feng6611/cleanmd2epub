#!/usr/bin/env python3
import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, Optional

from cleanmd.converter import MarkdownConverter

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="将Markdown文件转换为EPUB格式")

    parser.add_argument("input", help="输入的Markdown文件路径")
    parser.add_argument("-o", "--output", help="输出的EPUB文件路径")
    parser.add_argument("--title", help="书籍标题")
    parser.add_argument("--author", help="作者名")
    parser.add_argument("--language", help="语言代码(如zh-CN)")
    parser.add_argument("--cover", help="封面图片路径")
    parser.add_argument("--css", help="自定义CSS文件路径")
    parser.add_argument("--no-toc", action="store_true", help="不生成目录")
    parser.add_argument("--toc-depth", type=int, help="目录深度(默认3)")

    return parser.parse_args()


def create_config(args) -> Dict:
    """根据命令行参数创建配置"""
    config = {}

    if args.title:
        config["title"] = args.title
    if args.author:
        config["author"] = args.author
    if args.language:
        config["language"] = args.language
    if args.cover:
        config["cover-image"] = args.cover
    if args.css:
        config["css"] = args.css
    if args.no_toc:
        config["toc"] = False
    if args.toc_depth:
        config["toc-depth"] = args.toc_depth

    return config


def main():
    """主程序入口"""
    try:
        args = parse_args()

        # 验证输入文件
        input_file = Path(args.input)
        if not input_file.exists():
            logger.error(f"找不到输入文件: {input_file}")
            return 1
        if not input_file.suffix == ".md":
            logger.error("输入文件必须是Markdown格式(.md)")
            return 1

        # 设置输出文件
        output_file = args.output if args.output else None

        # 创建配置
        config = create_config(args)

        # 转换文件
        logger.info(f"开始处理文件: {input_file}")
        output_path = MarkdownConverter.convert_file(
            str(input_file), output_file, config
        )

        logger.info(f"转换完成: {output_path}")
        return 0

    except Exception as e:
        logger.error(f"转换失败: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
