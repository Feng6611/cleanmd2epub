#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

from ..core.config import Config
from ..core.document_parser import DocumentParser
from ..core.text_processor import TextProcessor
from ..core.epub_generator import EPUBGenerator
from ..utils.result_recorder import ResultRecorder
from ..utils.logger import get_logger

logger = get_logger(__name__)


async def process_book(input_file: str, output_file: str = None) -> None:
    """处理书籍文件

    Args:
        input_file: 输入文件路径
        output_file: 输出文件路径，如果不指定则使用输入文件名 + .epub
    """
    try:
        # 初始化配置
        logger.info("=" * 50)
        logger.info("开始处理书籍文件")
        logger.info(f"输入文件: {input_file}")
        logger.info("=" * 50)

        config = Config()
        logger.info("配置加载完成")

        # 创建处理器
        parser = DocumentParser(config)
        processor = TextProcessor(config)
        generator = EPUBGenerator(config)
        recorder = ResultRecorder(config)
        logger.info("所有处理器初始化完成")

        # 开始记录处理过程
        result = await recorder.start_processing(input_file)
        logger.info(f"处理记录将保存在: {recorder._get_result_dir(result)}")

        try:
            # 解析文档
            logger.info("\n" + "=" * 20 + " 第 1 步：解析文档 " + "=" * 20)
            logger.info(f"正在解析文档: {input_file}")
            document = await parser.parse_document(input_file)

            # 记录解析结果
            frontmatter = next(
                (
                    block
                    for block in document.blocks
                    if block.block_type == "frontmatter"
                ),
                None,
            )
            content_blocks = [
                block for block in document.blocks if block.block_type != "frontmatter"
            ]

            logger.info(f"文档解析完成:")
            logger.info(f"- 是否包含前置内容: {'是' if frontmatter else '否'}")
            logger.info(f"- 内容块数量: {len(content_blocks)}")
            if frontmatter:
                logger.info(f"- 前置内容长度: {len(frontmatter.content)} 字符")

            await recorder.record_parsing_result(result, frontmatter, content_blocks)
            logger.info("解析结果已保存")

            # 处理文档
            logger.info("\n" + "=" * 20 + " 第 2 步：处理文档内容 " + "=" * 20)
            logger.info("正在使用 Gemini API 处理文档内容...")
            processed_document = await processor.process_document(document)

            # 记录元数据提取结果
            if processed_document.metadata:
                logger.info("\n提取的元数据:")
                for key, value in processed_document.metadata.__dict__.items():
                    if value:
                        logger.info(f"- {key}: {value}")

                await recorder.record_metadata_extraction(
                    result,
                    processed_document.metadata,
                    next(
                        (
                            block
                            for block in processed_document.blocks
                            if block.block_type == "frontmatter"
                        ),
                        None,
                    ),
                )
                logger.info("元数据已保存")
            else:
                logger.warning("未能提取到元数据")

            # 记录处理后的内容块
            processed_blocks = [
                block
                for block in processed_document.blocks
                if block.block_type != "frontmatter"
            ]
            logger.info(f"\n处理完成:")
            logger.info(f"- 处理后的内容块数量: {len(processed_blocks)}")
            total_chars = sum(len(block.content) for block in processed_blocks)
            logger.info(f"- 总字符数: {total_chars}")

            await recorder.record_processed_blocks(result, processed_blocks)
            logger.info("处理后的内容已保存")

            # 生成 EPUB
            logger.info("\n" + "=" * 20 + " 第 3 步：生成 EPUB " + "=" * 20)
            logger.info("正在生成 EPUB...")
            epub_data = await generator.generate(
                processed_document, processed_document.metadata
            )
            logger.info(f"EPUB 生成完成，大小: {len(epub_data)/1024:.1f} KB")

            # 保存文件
            if not output_file:
                output_file = str(Path(input_file).with_suffix(".epub"))

            logger.info(f"正在保存 EPUB 文件: {output_file}")
            Path(output_file).write_bytes(epub_data)

            # 记录最终结果
            final_markdown = "\n\n".join(
                block.content for block in processed_document.blocks
            )
            await recorder.record_final_result(result, final_markdown, output_file)
            logger.info("最终结果已保存")

            logger.info("\n" + "=" * 20 + " 处理完成 " + "=" * 20)
            logger.info(f"- 输入文件: {input_file}")
            logger.info(f"- 输出文件: {output_file}")
            logger.info(f"- 处理记录: {recorder._get_result_dir(result)}")
            logger.info("=" * 50)

        except Exception as e:
            logger.error(f"\n处理过程中出现错误: {str(e)}")
            await recorder.record_error(result, e)
            raise

    except Exception as e:
        logger.error(f"\n处理失败: {str(e)}")
        logger.error("详细错误信息:", exc_info=True)
        raise


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.cli.process_book <input_file> [output_file]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    asyncio.run(process_book(input_file, output_file))
