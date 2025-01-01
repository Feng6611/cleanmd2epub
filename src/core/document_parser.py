import re
from typing import List, Optional, Tuple
from pathlib import Path

from ..interfaces.document_parser import (
    IDocumentParser,
    Document,
    Metadata,
    ContentBlock,
)
from ..config import Config
from ..utils.file_utils import read_markdown_file
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DocumentParser(IDocumentParser):
    """文档解析器实现类"""

    def __init__(self, config: Config):
        """初始化文档解析器

        Args:
            config: 配置对象
        """
        self.config = config
        self.content: Optional[str] = None
        self.frontmatter: Optional[str] = None
        self.mainmatter: Optional[str] = None

    async def parse_document(self, file_path: str) -> Document:
        """解析文档

        Args:
            file_path: MD文件路径

        Returns:
            Document对象
        """
        # 读取文件
        self.content = read_markdown_file(file_path)

        # 分割前置内容和正文
        self._split_document()

        # 提取元数据
        metadata = await self.extract_metadata()

        # 分割内容块
        blocks = await self.split_content()

        return Document(metadata=metadata, blocks=blocks, raw_content=self.content)

    def _split_document(self) -> None:
        """分割文档为前置内容和正文"""
        if not self.content:
            return

        # 使用正则表达式匹配正文开始标记
        patterns = [
            r"^第[一二三四五六七八九十]章",
            r"^引言",
            r"^序论",
            r"^前言",
            r"^目录",
        ]

        for pattern in patterns:
            matches = list(re.finditer(pattern, self.content, re.MULTILINE))
            if matches:
                match = matches[0]
                self.frontmatter = self.content[: match.start()].strip()
                self.mainmatter = self.content[match.start() :].strip()
                return

        # 如果没有找到分隔标记，则整个文档作为正文
        self.frontmatter = ""
        self.mainmatter = self.content

    async def extract_metadata(self) -> Metadata:
        """提取文档元数据"""
        if not self.frontmatter:
            return Metadata()

        # TODO: 使用 AI 提取元数据
        return Metadata()

    async def split_content(self) -> List[ContentBlock]:
        """分割文档内容"""
        blocks = []
        position = 0

        # 添加前置内容块
        if self.frontmatter:
            blocks.append(
                ContentBlock(
                    content=self.frontmatter,
                    block_type="frontmatter",
                    level=0,
                    position=position,
                )
            )
            position += 1

        # 分割正文
        if self.mainmatter:
            # 按标题分割
            current_block = ""
            current_level = 0

            for line in self.mainmatter.split("\n"):
                # 检查是否是标题行
                header_match = re.match(r"^(#{1,6})\s+(.+)$", line)
                if header_match:
                    # 保存当前块
                    if current_block:
                        blocks.append(
                            ContentBlock(
                                content=current_block.strip(),
                                block_type="content",
                                level=current_level,
                                position=position,
                            )
                        )
                        position += 1

                    # 开始新块
                    current_level = len(header_match.group(1))
                    current_block = line + "\n"
                else:
                    current_block += line + "\n"

            # 保存最后一个块
            if current_block:
                blocks.append(
                    ContentBlock(
                        content=current_block.strip(),
                        block_type="content",
                        level=current_level,
                        position=position,
                    )
                )

        return blocks
