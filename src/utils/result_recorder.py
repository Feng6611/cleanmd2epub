import json
import yaml
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..interfaces.result_recorder import IResultRecorder, ProcessingResult
from ..interfaces.document_parser import ContentBlock, Metadata
from ..config import Config
from .logger import get_logger

logger = get_logger(__name__)


class ResultRecorder(IResultRecorder):
    """结果记录器实现类"""

    def __init__(self, config: Config):
        """初始化结果记录器

        Args:
            config: 配置对象
        """
        self.config = config
        self.results_dir = Path(config.output_dir) / "results"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"结果记录器初始化完成，输出目录: {self.results_dir}")

    async def start_processing(self, input_file: str) -> ProcessingResult:
        """开始处理新文件

        Args:
            input_file: 输入文件路径

        Returns:
            处理结果对象
        """
        result = ProcessingResult(
            input_file=input_file, timestamp=datetime.now(), success=True
        )

        # 创建结果目录
        result_dir = self._get_result_dir(result)
        result_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"创建结果目录: {result_dir}")

        # 保存初始状态
        self._save_result(result)
        logger.debug("初始状态已保存")

        return result

    async def record_parsing_result(
        self,
        result: ProcessingResult,
        frontmatter: Optional[ContentBlock],
        content_blocks: List[ContentBlock],
    ) -> None:
        """记录解析结果

        Args:
            result: 处理结果对象
            frontmatter: 前置内容
            content_blocks: 内容块列表
        """
        result.frontmatter = frontmatter
        result.content_blocks = content_blocks

        # 保存解析结果
        result_dir = self._get_result_dir(result)
        logger.debug(f"正在保存解析结果到: {result_dir}")

        # 保存前置内容
        if frontmatter:
            frontmatter_file = result_dir / "1_frontmatter.md"
            frontmatter_file.write_text(frontmatter.content)
            logger.debug(f"前置内容已保存: {frontmatter_file}")

        # 保存内容块
        blocks_dir = result_dir / "1_content_blocks"
        blocks_dir.mkdir(exist_ok=True)
        for i, block in enumerate(content_blocks):
            block_file = blocks_dir / f"block_{i:03d}.md"
            block_file.write_text(block.content)
            logger.debug(f"内容块已保存: {block_file}")

        self._save_result(result)

    async def record_metadata_extraction(
        self,
        result: ProcessingResult,
        metadata: Optional[Metadata],
        processed_frontmatter: Optional[ContentBlock],
    ) -> None:
        """记录元数据提取结果

        Args:
            result: 处理结果对象
            metadata: 提取的元数据
            processed_frontmatter: 处理后的前置内容
        """
        result.extracted_metadata = metadata
        result.processed_frontmatter = processed_frontmatter

        result_dir = self._get_result_dir(result)
        logger.debug(f"正在保存元数据提取结果到: {result_dir}")

        # 保存元数据
        if metadata:
            metadata_file = result_dir / "2_extracted_metadata.yaml"
            metadata_file.write_text(
                yaml.dump(metadata.__dict__, allow_unicode=True, sort_keys=False)
            )
            logger.debug(f"元数据已保存: {metadata_file}")

        # 保存处理后的前置内容
        if processed_frontmatter:
            processed_frontmatter_file = result_dir / "2_processed_frontmatter.md"
            processed_frontmatter_file.write_text(processed_frontmatter.content)
            logger.debug(f"处理后的前置内容已保存: {processed_frontmatter_file}")

        self._save_result(result)

    async def record_douban_metadata(
        self, result: ProcessingResult, douban_metadata: Optional[Dict[str, Any]]
    ) -> None:
        """记录豆瓣元数据

        Args:
            result: 处理结果对象
            douban_metadata: 豆瓣元数据
        """
        result.douban_metadata = douban_metadata

        if douban_metadata:
            result_dir = self._get_result_dir(result)
            douban_file = result_dir / "3_douban_metadata.yaml"
            douban_file.write_text(
                yaml.dump(douban_metadata, allow_unicode=True, sort_keys=False)
            )
            logger.debug(f"豆瓣元数据已保存: {douban_file}")

        self._save_result(result)

    async def record_processed_blocks(
        self, result: ProcessingResult, processed_blocks: List[ContentBlock]
    ) -> None:
        """记录处理后的内容块

        Args:
            result: 处理结果对象
            processed_blocks: 处理后的内容块列表
        """
        result.processed_blocks = processed_blocks

        result_dir = self._get_result_dir(result)
        logger.debug(f"正在保存处理后的内容块到: {result_dir}")

        blocks_dir = result_dir / "4_processed_blocks"
        blocks_dir.mkdir(exist_ok=True)

        for i, block in enumerate(processed_blocks):
            block_file = blocks_dir / f"block_{i:03d}.md"
            block_file.write_text(block.content)
            logger.debug(f"处理后的内容块已保存: {block_file}")

        self._save_result(result)

    async def record_final_result(
        self, result: ProcessingResult, final_markdown: str, epub_file: str
    ) -> None:
        """记录最终结果

        Args:
            result: 处理结果对象
            final_markdown: 最终的 Markdown 文本
            epub_file: EPUB 文件路径
        """
        result.final_markdown = final_markdown
        result.epub_file = epub_file

        result_dir = self._get_result_dir(result)
        logger.debug(f"正在保存最终结果到: {result_dir}")

        # 保存最终的 Markdown 文件
        markdown_file = result_dir / "5_final.md"
        markdown_file.write_text(final_markdown)
        logger.debug(f"最终 Markdown 文件已保存: {markdown_file}")

        # 复制 EPUB 文件
        if Path(epub_file).exists():
            epub_target = result_dir / "5_final.epub"
            epub_target.write_bytes(Path(epub_file).read_bytes())
            logger.debug(f"EPUB 文件已复制: {epub_target}")

        self._save_result(result)

    async def record_error(self, result: ProcessingResult, error: Exception) -> None:
        """记录错误

        Args:
            result: 处理结果对象
            error: 错误信息
        """
        result.success = False
        result.error_message = str(error)
        logger.error(f"记录错误: {error}")
        self._save_result(result)

    def _get_result_dir(self, result: ProcessingResult) -> Path:
        """获取结果目录

        Args:
            result: 处理结果对象

        Returns:
            结果目录路径
        """
        timestamp = result.timestamp.strftime("%Y%m%d_%H%M%S")
        input_name = Path(result.input_file).stem
        return self.results_dir / f"{timestamp}_{input_name}"

    def _save_result(self, result: ProcessingResult) -> None:
        """保存处理结果

        Args:
            result: 处理结果对象
        """
        result_dir = self._get_result_dir(result)
        result_file = result_dir / "result.json"

        # 保存结果摘要
        result_file.write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
        )
        logger.debug(f"结果摘要已保存: {result_file}")
