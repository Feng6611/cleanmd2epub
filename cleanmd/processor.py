"""
处理 Markdown 文件的主要模块
"""

import os
import logging
from pathlib import Path
from typing import Optional

from cleanmd.splitter import MarkdownSplitter
from cleanmd.cleaner import MarkdownCleaner
from cleanmd.converter import MarkdownConverter
from cleanmd import config

# 配置日志
logger = logging.getLogger(__name__)


async def process_markdown(input_file: str) -> int:
    """
    处理 Markdown 文件的主函数

    Args:
        input_file: 输入文件路径

    Returns:
        int: 处理状态码（0表示成功）
    """
    try:
        # 创建基础输出目录（使用输入文件名作为目录名）
        file_stem = Path(input_file).stem
        base_output_dir = os.path.join(config.OUTPUT_DIR, file_stem)

        # 创建所需的子目录
        chunks_dir = os.path.join(base_output_dir, config.CHUNKS_DIR)
        cleaned_dir = os.path.join(base_output_dir, config.CLEANED_DIR)

        for dir_path in [base_output_dir, chunks_dir, cleaned_dir]:
            os.makedirs(dir_path, exist_ok=True)
            logger.info(f"创建目录: {dir_path}")

        # 设置输出文件路径
        original_file = os.path.join(base_output_dir, f"{file_stem}_original.md")
        chunks_file = os.path.join(chunks_dir, f"{file_stem}_chunks.md")
        cleaned_file = os.path.join(cleaned_dir, f"{file_stem}_cleaned.md")

        # 修改：最终文件放在项目目录下
        final_output_file = os.path.join(base_output_dir, f"{file_stem}_final.md")

        # 读取输入文件
        with open(input_file, "r", encoding="utf-8") as f:
            content = f.read()

        # 备份原始文件
        with open(original_file, "w", encoding="utf-8") as f:
            f.write(content)

        # 初始化组件
        splitter = MarkdownSplitter()
        cleaner = MarkdownCleaner()

        # 分割内容
        chunks = splitter.split_markdown(content)

        # 保存分段结果
        with open(chunks_file, "w", encoding="utf-8") as f:
            for i, chunk in enumerate(chunks, 1):
                f.write(f"\n\n{'='*50}\n分段 {i}:\n{'-'*50}\n{chunk}\n")

        # 清理每个分段
        cleaned_chunks = []
        for i, (context, content) in enumerate(chunks, 1):
            logger.info(f"\n处理分段 {i}/{len(chunks)}...")
            cleaned_chunk = await cleaner.clean_chunk_async(context, content)

            # 将每个处��后的分段保存到cleaned目录
            chunk_file = os.path.join(cleaned_dir, f"chunk_{str(i).zfill(3)}.md")
            with open(chunk_file, "w", encoding="utf-8") as f:
                f.write(cleaned_chunk)
            logger.info(f"分段 {i} 已保存到: {chunk_file}")

            cleaned_chunks.append(cleaned_chunk)

        # 合并清理后的内容
        cleaned_content = "\n\n".join(cleaned_chunks)

        # 保存清理后的文件到cleaned目录
        with open(cleaned_file, "w", encoding="utf-8") as f:
            f.write(cleaned_content)

        # 保存最终结果到项目根目录
        with open(final_output_file, "w", encoding="utf-8") as f:
            f.write(cleaned_content)

        # 新增：转换为EPUB
        converter = MarkdownConverter()
        epub_file = os.path.join(base_output_dir, f"{file_stem}_final.epub")
        await converter.convert_to_epub(final_output_file, epub_file)

        logger.info(f"\n处理完成！")
        logger.info(f"原始文件已备份至: {original_file}")
        logger.info(f"分段文件保存至: {chunks_file}")
        logger.info(f"清理后的分段文件保存在: {cleaned_dir}")
        logger.info(f"最终Markdown文件保存至: {final_output_file}")
        logger.info(f"EPUB文件保存至: {epub_file}")

        return 0

    except Exception as e:
        logger.error(f"处理过程中出现错误: {str(e)}")
        return 1
