from abc import ABC, abstractmethod
from typing import List
from dataclasses import dataclass


@dataclass
class Metadata:
    """文档元数据"""

    isbn: str | None = None
    title: str | None = None
    author: str | None = None
    publisher: str | None = None
    description: str | None = None


@dataclass
class ContentBlock:
    """文档内容块"""

    content: str
    block_type: str  # 'frontmatter' | 'content'
    level: int  # 标题层级，0表示正文
    position: int  # 在文档中的位置


@dataclass
class Document:
    """完整文档"""

    metadata: Metadata
    blocks: List[ContentBlock]
    raw_content: str


class IDocumentParser(ABC):
    """文档解析器接口"""

    @abstractmethod
    async def parse_document(self, file_path: str) -> Document:
        """解析文档

        Args:
            file_path: MD文件路径

        Returns:
            Document对象
        """
        pass

    @abstractmethod
    async def extract_metadata(self) -> Metadata:
        """提取文档元数据"""
        pass

    @abstractmethod
    async def split_content(self) -> List[ContentBlock]:
        """分割文档内容"""
        pass
