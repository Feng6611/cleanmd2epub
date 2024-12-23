import re
import logging
from typing import List, Tuple, Dict
from cleanmd import config

logger = logging.getLogger(__name__)


class MarkdownSplitter:
    def __init__(self):
        """初始化分段器,加载配置"""
        self.headers = config.MARKDOWN_HEADERS
        self.separators = config.MARKDOWN_SEPARATORS
        self.max_chunk_size = config.MAX_CHUNK_SIZE
        self.min_chunk_size = config.MIN_CHUNK_SIZE
        self.target_ratio = config.TARGET_RATIO
        self.target_chunk_size = int(self.max_chunk_size * self.target_ratio)
        logger.debug("分段器初始化完成")

    def split_markdown(
        self, content: str, preview_only: bool = False
    ) -> List[Tuple[str, str]]:
        """
        将Markdown文本分割成多个片段,优先按字数分块,同时保持章节完整性

        Args:
            content: 需要分割的Markdown文本
            preview_only: 是否仅返回第一个片段用于预览

        Returns:
            List[Tuple[str, str]]: 分割后的文本片段列表,每个元素是(context, content)
        """
        logger.info("开始分割Markdown文本")
        lines = content.split("\n")
        total_lines = len(lines)
        logger.info(f"文本总行数: {total_lines}")

        # 预处理:将文本分成章节
        sections = []  # [(header, content_lines, size)]
        current_header = ""
        current_lines = []
        current_size = 0

        # 修改：记录上一个标题行
        last_header_line = None

        for line in lines:
            is_header = any(line.startswith(header) for header in self.headers)

            if is_header:
                # 如果有上一个标题但没有内容，将上一个标题加入当前行
                if last_header_line and not current_lines:
                    current_lines.append(last_header_line)
                    current_size += len(last_header_line)

                # 如果当前段落不为空，保存当前段落
                if current_lines:
                    # 修改：不将标题作为context保存
                    sections.append(("", current_lines, current_size))
                    current_lines = []
                    current_size = 0

                current_header = line
                last_header_line = line
                # 修改：将标题添加到当前段落
                current_lines.append(line)
                current_size += len(line)

            else:
                if line.strip():  # 只有非空行才计入
                    current_lines.append(line)
                    current_size += len(line)
                    last_header_line = None  # 有内容后重置上一个标题记录

        # 添加最后一个章节
        if current_lines or last_header_line:
            if last_header_line and not current_lines:
                current_lines.append(last_header_line)
            sections.append(("", current_lines, current_size))

        # 合并章节成块
        chunks = []
        current_chunk_lines = []
        current_chunk_size = 0
        current_context = ""

        for header, lines, size in sections:
            # 如果当前章节本身就超过最大大小,需要单独处理
            if size > self.max_chunk_size:
                # 先保存当前累积的chunk
                if current_chunk_lines:
                    chunks.append((current_context, "\n".join(current_chunk_lines)))
                    if preview_only and chunks:
                        return chunks

                # 处理大章节
                chunk_lines = []
                chunk_size = 0
                for line in lines:
                    line_size = len(line)
                    if chunk_size + line_size > self.target_chunk_size and chunk_lines:
                        chunks.append(("", "\n".join(chunk_lines)))
                        if preview_only and chunks:
                            return chunks
                        chunk_lines = [line]
                        chunk_size = line_size
                    else:
                        chunk_lines.append(line)
                        chunk_size += line_size

                if chunk_lines:
                    chunks.append(("", "\n".join(chunk_lines)))
                    if preview_only and chunks:
                        return chunks

                current_chunk_lines = []
                current_chunk_size = 0
                current_context = ""
                continue

            # 判断是否可以将当前章节添加到当前chunk
            if current_chunk_size + size <= self.target_chunk_size:
                current_chunk_lines.extend(lines)
                current_chunk_size += size
            else:
                # 当前chunk已满,保存并开始新的chunk
                if current_chunk_lines:
                    chunks.append(("", "\n".join(current_chunk_lines)))
                    if preview_only and chunks:
                        return chunks
                current_chunk_lines = lines
                current_chunk_size = size

        # 保存最后一个chunk
        if current_chunk_lines:
            chunks.append(("", "\n".join(current_chunk_lines)))
            if preview_only and chunks:
                return chunks

        logger.info(f"文本分割完成,共生成 {len(chunks)} 个片段")
        return chunks

    def _is_complete_paragraph(self, lines: List[str]) -> bool:
        """判断一组行是否构成完整段落"""
        if not lines:
            return False
        # 段落应该以空行或标题结束
        last_line = lines[-1].strip()
        return (not last_line) or any(last_line.startswith(h) for h in self.headers)
