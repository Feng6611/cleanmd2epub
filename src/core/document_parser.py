import re
from typing import List, Optional, Tuple
from pathlib import Path
import aiofiles
from datetime import datetime

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
        self.content = None

    async def parse_document(self, file_path: str) -> Document:
        """解析文档"""
        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            self.content = await f.read()

        # 分离前置内容和主体内容
        frontmatter, main_content = self._split_document(self.content)

        # 分块处理
        blocks = self.split_content(frontmatter, main_content)

        # 输出分块结果
        self._output_blocks(blocks)

        return Document(
            metadata=Metadata(),  # 使用空的元数据对象，后续由 TextProcessor 处理前置部分时填充
            blocks=blocks,
            raw_content=self.content,
        )

    def _split_document(self, content: str) -> Tuple[str, str]:
        """分离前置内容和主体内容

        Args:
            content: 完整的文档内容

        Returns:
            Tuple[str, str]: (前置内容, 主体内容)
            - 前置内容：包含书名、作者、版权等基本信息
            - 主体内容：从第一个分隔标记（如总序、目录等）开始的所有内容
        """
        # 定义更简洁的前置内容结束标记的正则表达式
        split_markers = [
            r"(?m)^#+\s*(?:第[一二三四五六七八九十百千万]+章|\d+|Chapter \d+)\s*$",  # 章节标记
            r"(?m)^#*\s*(?:目\s*录|目录索引|内容目录|章节目录|Contents|Table of Contents|TOC|Index)\s*$",  # 目录相关
            r"(?m)^#+\s*(?:引言|序言|前言|导言|序论|导论|绪论|总序|自序|代序|译序|编序|总论|概论|综述)\s*$",  # 常见正文开始标记（中文）
            r"(?m)^#+\s*(?:Introduction|Preface|Foreword|Prologue|Prolegomenon|Preamble|Overview|Abstract|Synopsis|Summary|Outline)\s*$",  # 常见正文开始标记（英文）
            r"(?m)^#+\s*(?:正文|正文开始|Main Text|Start|Beginning)\s*$",  # 其他可能的标记
        ]
        combined_pattern = "|".join(split_markers)

        # 尝试查找第一个匹配的标记
        match = re.search(combined_pattern, content)

        if match:
            # 分隔标记之前的内容作为前置部分
            frontmatter = content[: match.start()].strip()
            # 分隔标记及之后的内容作为主体部分
            main_content = content[match.start() :].strip()
            logger.debug(f"找到分隔标记: {match.group()}")
            logger.debug(f"前置部分长度: {len(frontmatter)} 字符")
            logger.debug(f"主体部分长度: {len(main_content)} 字符")
            return frontmatter, main_content

        # 如果没有找到任何标记，将整个内容作为主体内容
        logger.debug("未找到分隔标记，将整个内容作为主体内容")
        return "", content.strip()

    def split_content(self, frontmatter: str, main_content: str) -> List[ContentBlock]:
        """分块处理内容"""
        blocks = []

        # 将前置内容作为一个整体的 block
        if frontmatter:
            blocks.append(
                ContentBlock(
                    block_type="frontmatter", level=0, position=0, content=frontmatter
                )
            )

        # 处理主体内容
        if main_content:
            # 先按段落分割
            paragraphs = [p for p in main_content.split("\n\n") if p.strip()]
            current_block = []
            current_size = 0
            current_pos = len(blocks)

            for para in paragraphs:
                para_size = self._count_chars(para)  # 使用加权字符计数

                # 如果当前块为空，直接添加
                if not current_block:
                    current_block.append(para)
                    current_size = para_size
                    continue

                # 如果添加这个段落后不会超过最大大小，就添加到当前块
                if current_size + para_size <= self.config.max_block_size:
                    current_block.append(para)
                    current_size += para_size
                else:
                    # 保存当前块
                    blocks.append(
                        ContentBlock(
                            block_type="content",
                            level=0,
                            position=current_pos,
                            content="\n\n".join(current_block).strip(),
                        )
                    )
                    current_pos += 1
                    # 开始新块
                    current_block = [para]
                    current_size = para_size

            # 保存最后一个块
            if current_block:
                blocks.append(
                    ContentBlock(
                        block_type="content",
                        level=0,
                        position=current_pos,
                        content="\n\n".join(current_block).strip(),
                    )
                )

            # 最后再检查一遍，合并太小的块
            blocks = self._adjust_block_sizes(blocks)

        return blocks

    def _count_chars(self, text: str) -> int:
        """计算文本的加权字符数
        - 中文字符权重为2
        - 其他所有字符权重为1（包括英文、数字、空格、标点）
        """
        return sum(2 if "\u4e00" <= char <= "\u9fff" else 1 for char in text)

    def _adjust_block_sizes(self, blocks: List[ContentBlock]) -> List[ContentBlock]:
        """循环合并小块，直到无法再合并"""
        if not blocks:
            return blocks

        # 先处理大块的拆分
        split_blocks = []
        for block in blocks:
            current_size = self._count_chars(block.content)
            if current_size > self.config.max_block_size:
                split_blocks.extend(
                    self._split_large_block(block, self.config.max_block_size)
                )
            else:
                split_blocks.append(block)

        # 循环合并，直到无法再合并
        while True:
            merged_blocks = []
            i = 0
            merged_count = 0  # 记录本轮合并次数

            while i < len(split_blocks):
                current_block = split_blocks[i]
                current_size = self._count_chars(current_block.content)

                # 尝试向后合并，直到达到最大大小或没有更多块
                while i + 1 < len(split_blocks):
                    next_block = split_blocks[i + 1]
                    next_size = self._count_chars(next_block.content)
                    combined_size = current_size + next_size

                    # 如果合并后的大小在允许范围内，就合并
                    # 允许超过max_size最多20%
                    if combined_size <= self.config.max_block_size * 1.2:
                        current_block = ContentBlock(
                            block_type=current_block.block_type,
                            level=min(current_block.level, next_block.level),
                            position=len(merged_blocks),
                            content=current_block.content + "\n\n" + next_block.content,
                        )
                        current_size = combined_size
                        i += 1
                        merged_count += 1
                    # 如果当前块太小，即使超过max_size也要尝试合并
                    elif current_size < self.config.min_block_size:
                        current_block = ContentBlock(
                            block_type=current_block.block_type,
                            level=min(current_block.level, next_block.level),
                            position=len(merged_blocks),
                            content=current_block.content + "\n\n" + next_block.content,
                        )
                        current_size = combined_size
                        i += 1
                        merged_count += 1
                    else:
                        break

                merged_blocks.append(current_block)
                i += 1

            # 更新块的位置信息
            for i, block in enumerate(merged_blocks):
                block.position = i

            # 如果本轮没有进行任何合并，说明已经无法继续合并，退出循环
            if merged_count == 0:
                return merged_blocks

            # 否则继续下一轮合并
            split_blocks = merged_blocks

    def _split_large_block(
        self, block: ContentBlock, max_size: int
    ) -> List[ContentBlock]:
        """使用更智能的方式拆分大块"""
        content = block.content
        if self._count_chars(content) <= max_size:
            return [block]

        # 首先尝试在段落边界分割
        paragraphs = [p for p in content.split("\n\n") if p.strip()]
        if len(paragraphs) > 1:
            current_block = []
            current_size = 0
            blocks = []

            for para in paragraphs:
                para_size = self._count_chars(para)
                # 如果单个段落就超过最大大小，需要单独处理
                if para_size > max_size:
                    # 先保存当前累积的块
                    if current_block:
                        blocks.append(
                            ContentBlock(
                                block_type=block.block_type,
                                level=block.level,
                                position=len(blocks),
                                content="\n\n".join(current_block).strip(),
                            )
                        )
                        current_block = []
                        current_size = 0

                    # 处理大段落
                    blocks.extend(
                        self._split_by_sentences(
                            ContentBlock(
                                block_type=block.block_type,
                                level=block.level,
                                position=len(blocks),
                                content=para,
                            ),
                            max_size,
                        )
                    )
                    continue

                if current_size + para_size <= max_size:
                    current_block.append(para)
                    current_size += para_size
                else:
                    if current_block:
                        blocks.append(
                            ContentBlock(
                                block_type=block.block_type,
                                level=block.level,
                                position=len(blocks),
                                content="\n\n".join(current_block).strip(),
                            )
                        )
                    current_block = [para]
                    current_size = para_size

            if current_block:
                blocks.append(
                    ContentBlock(
                        block_type=block.block_type,
                        level=block.level,
                        position=len(blocks),
                        content="\n\n".join(current_block).strip(),
                    )
                )
            return blocks

        # 如果没有段落分隔，使用句子分割
        return self._split_by_sentences(block, max_size)

    def _split_by_sentences(
        self, block: ContentBlock, max_size: int
    ) -> List[ContentBlock]:
        """按句子分割内容"""
        content = block.content
        # 扩展句子分隔符
        sentence_patterns = [
            r"([。！？])",  # 中文句末
            r"([.!?](?:\s|$))",  # 英文句末
        ]
        pattern = "|".join(sentence_patterns)
        sentences = []
        last_end = 0

        for match in re.finditer(pattern, content):
            end = match.end()
            sentence = content[last_end:end].strip()
            if sentence:
                sentences.append(sentence)
            last_end = end

        # 添加最后一部分
        if last_end < len(content):
            remaining = content[last_end:].strip()
            if remaining:
                sentences.append(remaining)

        blocks = []
        current_block = []
        current_size = 0

        for sentence in sentences:
            sent_size = self._count_chars(sentence)
            if sent_size > max_size:
                # 如果单个句子超过最大大小，强制分割
                if current_block:
                    blocks.append(
                        ContentBlock(
                            block_type=block.block_type,
                            level=block.level,
                            position=len(blocks),
                            content="".join(current_block).strip(),
                        )
                    )
                    current_block = []
                    current_size = 0

                blocks.extend(
                    self._force_split_block(
                        ContentBlock(
                            block_type=block.block_type,
                            level=block.level,
                            position=len(blocks),
                            content=sentence,
                        ),
                        max_size,
                    )
                )
                continue

            if current_size + sent_size <= max_size:
                current_block.append(sentence)
                current_size += sent_size
            else:
                if current_block:
                    blocks.append(
                        ContentBlock(
                            block_type=block.block_type,
                            level=block.level,
                            position=len(blocks),
                            content="".join(current_block).strip(),
                        )
                    )
                current_block = [sentence]
                current_size = sent_size

        if current_block:
            blocks.append(
                ContentBlock(
                    block_type=block.block_type,
                    level=block.level,
                    position=len(blocks),
                    content="".join(current_block).strip(),
                )
            )

        return blocks

    def _force_split_block(
        self, block: ContentBlock, max_size: int
    ) -> List[ContentBlock]:
        """在没有自然分割点时强制分割块"""
        content = block.content
        blocks = []
        remaining = content
        current_pos = block.position

        while remaining:
            # 计算当前可用的最大长度
            count = 0
            length = 0
            for i, char in enumerate(remaining):
                weight = 2 if "\u4e00" <= char <= "\u9fff" else 1
                if count + weight > max_size:
                    break
                count += weight
                length = i + 1

            # 确保至少分割出一个字符
            length = max(1, length)

            blocks.append(
                ContentBlock(
                    block_type=block.block_type,
                    level=block.level,
                    position=current_pos,
                    content=remaining[:length].strip(),
                )
            )
            remaining = remaining[length:].strip()
            current_pos += 1

        return blocks

    def _output_blocks(self, blocks: List[ContentBlock]) -> None:
        """输出分块结果到文件"""
        output_dir = Path("output/blocks")
        output_dir.mkdir(parents=True, exist_ok=True)

        # 生成输出文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"blocks_{timestamp}.md"

        # 写入分块结果
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# 文档分块结果\n\n")

            # 统计信息
            f.write("## 统计信息\n\n")
            f.write(f"- 总块数: {len(blocks)}\n")
            f.write(
                f"- 前置内容块数: {len([b for b in blocks if b.block_type == 'frontmatter'])}\n"
            )
            f.write(
                f"- 主体内容块数: {len([b for b in blocks if b.block_type == 'content'])}\n\n"
            )

            # 详细分块信息
            f.write("## 详细分块信息\n\n")
            for i, block in enumerate(blocks, 1):
                f.write(f"### 块 {i}\n\n")
                f.write(f"- 类型: {block.block_type}\n")
                f.write(f"- 级别: {block.level}\n")
                f.write(f"- 位置: {block.position}\n")
                f.write(f"- 内容长度: {len(block.content)} 字符\n")
                f.write(
                    f"- 计数长度: {self._count_chars(block.content)} (英文1/中文2)\n"
                )

                # 内容预览
                f.write("\n内容预览:\n")
                f.write("```markdown\n")
                lines = block.content.split("\n")
                if len(lines) > 6:
                    preview = "\n".join(lines[:3] + ["..."] + lines[-3:])
                else:
                    preview = block.content
                f.write(preview)
                f.write("\n```\n\n")
                f.write("-" * 80 + "\n\n")

        logger.info(f"分块结果已输出到: {output_path}")

        # 同时输出每个块的完整内容到单独的文件
        blocks_dir = output_dir / f"blocks_{timestamp}"
        blocks_dir.mkdir(exist_ok=True)

        for i, block in enumerate(blocks, 1):
            block_type = block.block_type
            block_path = blocks_dir / f"{i:03d}_{block_type}.md"
            with open(block_path, "w", encoding="utf-8") as f:
                f.write(block.content)
