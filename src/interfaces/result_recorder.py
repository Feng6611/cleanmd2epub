from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .document_parser import Document, ContentBlock, Metadata


@dataclass
class ProcessingResult:
    """处理结果记录"""

    # 基本信息
    input_file: str
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None

    # 文档解析结果
    frontmatter: Optional[ContentBlock] = None
    content_blocks: Optional[List[ContentBlock]] = None

    # AI 处理结果
    extracted_metadata: Optional[Metadata] = None
    processed_frontmatter: Optional[ContentBlock] = None
    processed_blocks: Optional[List[ContentBlock]] = None

    # 豆瓣元数据
    douban_metadata: Optional[Dict[str, Any]] = None

    # 最终结果
    final_markdown: Optional[str] = None
    epub_file: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "input_file": self.input_file,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "error_message": self.error_message,
            "frontmatter": self.frontmatter.content if self.frontmatter else None,
            "content_blocks": (
                [block.content for block in self.content_blocks]
                if self.content_blocks
                else None
            ),
            "extracted_metadata": (
                self.extracted_metadata.__dict__ if self.extracted_metadata else None
            ),
            "processed_frontmatter": (
                self.processed_frontmatter.content
                if self.processed_frontmatter
                else None
            ),
            "processed_blocks": (
                [block.content for block in self.processed_blocks]
                if self.processed_blocks
                else None
            ),
            "douban_metadata": self.douban_metadata,
            "final_markdown": self.final_markdown,
            "epub_file": self.epub_file,
        }


class IResultRecorder:
    """结果记录器接口"""

    async def start_processing(self, input_file: str) -> ProcessingResult:
        """开始处理新文件

        Args:
            input_file: 输入文件路径

        Returns:
            处理结果对象
        """
        raise NotImplementedError

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
        raise NotImplementedError

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
        raise NotImplementedError

    async def record_douban_metadata(
        self, result: ProcessingResult, douban_metadata: Optional[Dict[str, Any]]
    ) -> None:
        """记录豆瓣元数据

        Args:
            result: 处理结果对象
            douban_metadata: 豆瓣元数据
        """
        raise NotImplementedError

    async def record_processed_blocks(
        self, result: ProcessingResult, processed_blocks: List[ContentBlock]
    ) -> None:
        """记录处理后的内容块

        Args:
            result: 处理结果对象
            processed_blocks: 处理后的内容块列表
        """
        raise NotImplementedError

    async def record_final_result(
        self, result: ProcessingResult, final_markdown: str, epub_file: str
    ) -> None:
        """记录最终结果

        Args:
            result: 处理结果对象
            final_markdown: 最终的 Markdown 文本
            epub_file: EPUB 文件路径
        """
        raise NotImplementedError

    async def record_error(self, result: ProcessingResult, error: Exception) -> None:
        """记录错误

        Args:
            result: 处理结果对象
            error: 错误信息
        """
        raise NotImplementedError
