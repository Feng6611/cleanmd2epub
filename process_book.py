import asyncio
import logging
from pathlib import Path
from src.config import Config
from src.core.document_parser import DocumentParser
from src.core.text_processor import TextProcessor
from src.core.epub_generator import EPUBGenerator
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def process_book(input_file: str, output_file: str):
    """处理书籍文件

    Args:
        input_file: 输入文件路径
        output_file: 输出文件路径
    """
    try:
        # 初始化配置
        config = Config.from_env()

        # 创建处理器
        parser = DocumentParser(config)
        processor = TextProcessor(config)
        generator = EPUBGenerator(config)

        # 解析文档
        logger.info("正在解析文档...")
        document = await parser.parse_document(input_file)

        # 处理文档
        logger.info("正在处理文档内容...")
        processed_doc = await processor.process_document(document)

        # 生成 EPUB
        logger.info("正在生成 EPUB...")
        epub_data = await generator.generate(processed_doc, processed_doc.metadata)

        # 保存文件
        logger.info(f"正在保存到 {output_file}...")
        Path(output_file).write_bytes(epub_data)

        logger.info("处理完成！")

    except Exception as e:
        logger.error(f"处理失败: {e}")
        raise


if __name__ == "__main__":
    input_file = "跨文化阅读启示 张隆溪.md"
    output_file = "跨文化阅读启示 张隆溪.epub"

    # 设置日志级别
    logging.basicConfig(level=logging.INFO)

    # 运行处理
    asyncio.run(process_book(input_file, output_file))
