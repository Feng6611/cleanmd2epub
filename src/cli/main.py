import asyncio
import click
from pathlib import Path
from typing import Optional
from datetime import datetime
import json

from ..core.document_parser import DocumentParser
from ..core.text_processor import TextProcessor
from ..core.epub_generator import EPUBGenerator
from ..utils.douban_crawler import DoubanCrawler
from ..interfaces.document_parser import Document, Metadata

# 暂时注释掉 ResultRecorder
# from ..utils.result_recorder import ResultRecorder
from ..config import Config
from ..utils.logger import get_logger

logger = get_logger(__name__)


def create_output_dir(input_file: str) -> Path:
    """创建输出目录"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = Path(input_file).stem
    output_dir = Path("output") / f"{base_name}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def save_json(data: dict, file_path: Path) -> None:
    """保存 JSON 数据"""
    file_path.parent.mkdir(parents=True, exist_ok=True)  # 确保父目录存在
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def async_main(
    input_file: str,
    output: Optional[str] = None,
    cache: bool = True,
    debug: bool = False,
):
    """异步主函数"""
    try:
        # 设置日志级别
        if debug:
            logger.setLevel("DEBUG")

        # 创建输出目录
        output_dir = create_output_dir(input_file)
        logger.info(f"输出目录: {output_dir}")

        # 初始化配置
        config = Config()
        config.cache_enabled = cache

        try:
            # 1. 解析文档
            logger.info("开始解析文档...")
            parser = DocumentParser(config)
            document = await parser.parse_document(input_file)

            # 保存前置部分和主体部分
            doc_split_dir = output_dir / "1_doc_split"
            doc_split_dir.mkdir(parents=True, exist_ok=True)

            frontmatter = next(
                (
                    block
                    for block in document.blocks
                    if block.block_type == "frontmatter"
                ),
                None,
            )
            if frontmatter:
                (doc_split_dir / "frontmatter.md").write_text(frontmatter.content)
                logger.info("已保存前置部分到: frontmatter.md")

            content_blocks = [
                block for block in document.blocks if block.block_type == "content"
            ]
            main_content = "\n\n".join(block.content for block in content_blocks)
            (doc_split_dir / "main_content.md").write_text(main_content)
            logger.info("已保存主体部分到: main_content.md")

            # 保存分块结果
            blocks_dir = output_dir / "2_blocks"
            blocks_dir.mkdir(parents=True, exist_ok=True)
            for i, block in enumerate(document.blocks, 1):
                block_file = blocks_dir / f"{i:03d}_{block.block_type}.md"
                block_file.write_text(block.content)
                logger.info(f"已保存分块 {i} 到: {block_file.name}")

            # 保存分块统计信息
            blocks_info = {
                "total_blocks": len(document.blocks),
                "frontmatter_blocks": len(
                    [b for b in document.blocks if b.block_type == "frontmatter"]
                ),
                "content_blocks": len(
                    [b for b in document.blocks if b.block_type == "content"]
                ),
                "blocks": [
                    {
                        "index": i,
                        "type": block.block_type,
                        "length": len(block.content),
                        "preview": (
                            block.content[:100] + "..."
                            if len(block.content) > 100
                            else block.content
                        ),
                    }
                    for i, block in enumerate(document.blocks, 1)
                ],
            }
            save_json(blocks_info, blocks_dir / "blocks_info.json")
            logger.info("已保存分块统计信息到: blocks_info.json")

            logger.info("文档解析完成")

            # 2. 处理文本
            logger.info("开始处理文本...")
            processor = TextProcessor(config)

            # 2.1 首先处理前置内容，提取元数据
            logger.info("处理前置内容，提取元数据...")
            metadata = None
            if frontmatter:
                metadata = await processor._extract_metadata(frontmatter)
                if metadata:
                    document.metadata = metadata
                    logger.info(f"成功提取元数据: {metadata}")

                    # 保存提取的元数据
                    metadata_dir = output_dir / "3_metadata"
                    metadata_dir.mkdir(parents=True, exist_ok=True)
                    extracted_metadata_file = metadata_dir / "extracted_metadata.json"
                    save_json(metadata.__dict__, extracted_metadata_file)
                    logger.info("已保存提取的元数据到: extracted_metadata.json")

                    # 2.2 异步获取豆瓣元数据
                    async def fetch_douban_metadata():
                        try:
                            crawler = DoubanCrawler(config)
                            douban_data = None

                            # 优先使用 ISBN 获取
                            if metadata.isbn:
                                logger.info(
                                    f"使用 ISBN 获取豆瓣元数据: {metadata.isbn}"
                                )
                                douban_data = await crawler.get_book_metadata(
                                    metadata.isbn
                                )

                            # 如果没有 ISBN 或获取失败，使用书名
                            if not douban_data and metadata.title:
                                logger.info(f"使用书名获取豆瓣元数据: {metadata.title}")
                                douban_data = await crawler.get_book_metadata_by_title(
                                    metadata.title
                                )

                            if douban_data:
                                # 保存豆瓣元数据
                                douban_file = metadata_dir / "douban_metadata.json"
                                save_json(douban_data, douban_file)
                                logger.info("已保存豆瓣元数据到: douban_metadata.json")

                                # 更新元数据
                                metadata.title = (
                                    douban_data.get("title") or metadata.title
                                )
                                metadata.author = (
                                    douban_data.get("author") or metadata.author
                                )
                                metadata.publisher = (
                                    douban_data.get("publisher") or metadata.publisher
                                )
                                metadata.description = (
                                    douban_data.get("description")
                                    or metadata.description
                                )
                                metadata.douban_metadata = douban_data

                                # 保存更新后的元数据
                                updated_metadata_file = (
                                    metadata_dir / "updated_metadata.json"
                                )
                                save_json(metadata.__dict__, updated_metadata_file)
                                logger.info(
                                    "已保存更新后的元数据到: updated_metadata.json"
                                )
                            else:
                                logger.warning("未能获取豆瓣元数据")
                        except Exception as e:
                            logger.error(f"获取豆瓣元数据时出错: {e}")

                else:
                    logger.warning("未能从前置内容提取元数据")

            # 2.3 并行处理：获取豆瓣数据和处理内容块
            tasks = []

            # 如果有元数据，添加获取豆瓣数据的任务
            if metadata:
                tasks.append(asyncio.create_task(fetch_douban_metadata()))

            # 添加处理内容的任务
            logger.info("开始处理内容块...")
            tasks.append(asyncio.create_task(processor.process_document(document)))

            # 等待所有任务完成
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果
            processed_doc = None
            for result in results:
                if isinstance(result, Document):
                    processed_doc = result
                elif isinstance(result, Exception):
                    logger.error(f"任务执行出错: {result}")

            if not processed_doc:
                raise click.ClickException("文档处理失败")

            # 4. 保存清洗结果
            cleaned_dir = output_dir / "4_cleaned"
            cleaned_dir.mkdir(parents=True, exist_ok=True)

            # 保存每个块的清洗结果和对比信息
            comparison_file = cleaned_dir / "cleaning_comparison.md"
            with open(comparison_file, "w", encoding="utf-8") as f:
                f.write("# 文本清洗对比报告\n\n")
                for i, (orig_block, cleaned_block) in enumerate(
                    zip(document.blocks, processed_doc.blocks), 1
                ):
                    # 写入对比文件
                    f.write(f"## 块 {i} ({cleaned_block.block_type})\n\n")
                    f.write("### 原始内容\n")
                    f.write("```markdown\n")
                    f.write(orig_block.content)
                    f.write("\n```\n\n")
                    f.write("### 清洗后内容\n")
                    f.write("```markdown\n")
                    f.write(cleaned_block.content)
                    f.write("\n```\n\n")
                    f.write("---\n\n")

                    # 保存单独的文件
                    cleaned_block_file = (
                        cleaned_dir / f"{i:03d}_{cleaned_block.block_type}_cleaned.md"
                    )
                    cleaned_block_file.write_text(cleaned_block.content)
                    logger.info(f"已保存清洗后的块 {i} 到: {cleaned_block_file.name}")

            logger.info("已生成清洗对比报告: cleaning_comparison.md")

            # 保存完整的清洗后文档
            frontmatter_block = next(
                (
                    block
                    for block in processed_doc.blocks
                    if block.block_type == "frontmatter"
                ),
                None,
            )
            content_blocks = [
                block for block in processed_doc.blocks if block.block_type == "content"
            ]

            full_content = []
            if frontmatter_block:
                full_content.append(frontmatter_block.content)
            full_content.extend(block.content for block in content_blocks)

            cleaned_content = "\n\n".join(full_content)
            (cleaned_dir / "full_cleaned.md").write_text(cleaned_content)
            logger.info("已保存完整的清洗后文档到: full_cleaned.md")

            # 5. 生成 EPUB
            logger.info("开始生成 EPUB...")
            generator = EPUBGenerator(config)
            epub_data = await generator.generate(processed_doc, processed_doc.metadata)

            # 6. 验证 EPUB
            logger.info("正在验证 EPUB...")
            if not await generator.validate_output(epub_data):
                raise click.ClickException("EPUB 验证失败")

            # 保存 EPUB
            final_dir = output_dir / "5_final"
            final_dir.mkdir(parents=True, exist_ok=True)

            output_path = (
                Path(output) if output else Path(input_file).with_suffix(".epub")
            )
            output_path.write_bytes(epub_data)
            (final_dir / "final.epub").write_bytes(epub_data)
            logger.info(f"已生成 EPUB 文件到: {output_path}")

            # 保存处理日志
            log_file = output_dir / "process.log"
            log_file.write_text(
                f"""处理完成！

输入文件: {input_file}
输出文件: {output_path}
处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

输出目录结构:
1. 文档拆分 (1_doc_split/)
   - frontmatter.md: 前置部分
   - main_content.md: 主体部分

2. 分块结果 (2_blocks/)
   - blocks_info.json: 分块统计信息
   - [001-999]_[type].md: 各个分块内容

3. 元数据 (3_metadata/)
   - extracted_metadata.json: 提取的元数据
   - douban_metadata.json: 豆瓣元数据（如果有）
   - updated_metadata.json: 更新后的元数据

4. 清洗结果 (4_cleaned/)
   - [001-999]_[type]_cleaned.md: 各个块的清洗结果
   - full_cleaned.md: 完整的清洗后文档

5. 最终输出 (5_final/)
   - final.epub: 生成的EPUB文件
"""
            )

        except Exception as e:
            logger.error(f"处理过程中出错: {e}")
            raise

    except Exception as e:
        logger.error(f"处理失败: {e}")
        raise click.Abort()


def sync_main(
    input_file: str,
    output: Optional[str] = None,
    cache: bool = True,
    debug: bool = False,
):
    """同步包装函数"""
    return asyncio.run(async_main(input_file, output, cache, debug))


@click.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="输出文件路径")
@click.option("--cache/--no-cache", default=True, help="是否使用缓存")
@click.option("--debug", is_flag=True, help="启用调试模式")
def main(
    input_file: str,
    output: Optional[str] = None,
    cache: bool = True,
    debug: bool = False,
):
    """将 OCR 识别后的 Markdown 文件转换为 EPUB 电子书"""
    return sync_main(input_file, output, cache, debug)


if __name__ == "__main__":
    main()  # 这里调用同步的入口点函数
