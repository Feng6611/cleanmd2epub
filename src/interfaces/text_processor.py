from abc import ABC, abstractmethod
from typing import List
from dataclasses import dataclass
from .document_parser import ContentBlock, Document


@dataclass
class ProcessedBlock(ContentBlock):
    """处理后的内容块"""

    original_content: str
    changes_made: List[str]
    confidence_score: float


class ITextProcessor(ABC):
    """文本处理器接口"""

    @abstractmethod
    async def process_block(self, block: ContentBlock) -> ProcessedBlock:
        """处理单个内容块

        Args:
            block: 待处理的内容块

        Returns:
            处理后的内容块
        """
        pass

    @abstractmethod
    async def validate_result(self, block: ProcessedBlock) -> bool:
        """验证处理结果

        Args:
            block: 处理后的内容块

        Returns:
            验证是否通过
        """
        pass

    @abstractmethod
    async def merge_blocks(self, blocks: List[ProcessedBlock]) -> Document:
        """合并处理后的内容块

        Args:
            blocks: 处理后的内容块列表

        Returns:
            合并后的文档
        """
        pass
