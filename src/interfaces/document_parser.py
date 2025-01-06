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

    def to_dict(self) -> dict:
        """转换为字典，用于 JSON 序列化"""
        return {
            "content": self.content,
            "block_type": self.block_type,
            "level": self.level,
            "position": self.position,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ContentBlock":
        """从字典创建对象"""
        return cls(
            content=data["content"],
            block_type=data["block_type"],
            level=data["level"],
            position=data["position"],
        )


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
    def split_content(self, frontmatter: str, main_content: str) -> List[ContentBlock]:
        """分割文档内容

        Args:
            frontmatter: 前置内容
            main_content: 主体内容

        Returns:
            内容块列表
        """
        pass
