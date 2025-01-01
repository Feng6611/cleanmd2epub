import asyncio
from typing import List, Dict
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

from ..interfaces.text_processor import ITextProcessor, ProcessedBlock
from ..interfaces.document_parser import ContentBlock, Document
from ..config import Config
from ..utils.logger import get_logger

logger = get_logger(__name__)


class TextProcessor(ITextProcessor):
    """文本处理器实现类"""

    def __init__(self, config: Config):
        """初始化文本处理器

        Args:
            config: 配置对象
        """
        self.config = config
        self.model = self._init_model()
        self._cache: Dict[str, ProcessedBlock] = {}

    def _init_model(self):
        """初始化 Gemini 模型"""
        genai.configure(api_key=self.config.gemini_api_key)
        return genai.GenerativeModel("gemini-1.0-pro")

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _call_gemini(self, prompt: str) -> str:
        """调用 Gemini API

        Args:
            prompt: 提示词

        Returns:
            API 响应文本
        """
        try:
            response = await self.model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini API 调用失败: {str(e)}")
            raise

    async def process_block(self, block: ContentBlock) -> ProcessedBlock:
        """处理单个内容块

        Args:
            block: 待处理的内容块

        Returns:
            处理后的内容块
        """
        # 检查缓存
        cache_key = f"{block.content}_{block.block_type}_{block.level}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 构建提示词
        prompt = self._build_prompt(block)

        # 调用 API
        response = await self._call_gemini(prompt)

        # 创建处理后的内容块
        processed_block = ProcessedBlock(
            content=response,
            block_type=block.block_type,
            level=block.level,
            position=block.position,
            original_content=block.content,
            changes_made=[],  # TODO: 分析变更
            confidence_score=1.0,  # TODO: 计算置信度
        )

        # 缓存结果
        self._cache[cache_key] = processed_block

        return processed_block

    def _build_prompt(self, block: ContentBlock) -> str:
        """构建提示词

        Args:
            block: 内容块

        Returns:
            提示词
        """
        if block.block_type == "frontmatter":
            return (
                "作为一个epub文件编辑，从读者的角度考虑，"
                "需要删除和保存的部分，并做基本的校对。\n\n"
                f"输入文本:\n{block.content}"
            )
        else:
            return (
                "请清洗scan pdf转化后的markdown文件内容，"
                "校对文本、调整段落、删除ocr的错误数据。"
                "保持markdown格式。\n\n"
                f"输入文本:\n{block.content}"
            )

    async def validate_result(self, block: ProcessedBlock) -> bool:
        """验证处理结果

        Args:
            block: 处理后的内容块

        Returns:
            验证是否通过
        """
        # TODO: 实现更复杂的验证逻辑
        return len(block.content) > 0 and block.content != block.original_content

    async def merge_blocks(self, blocks: List[ProcessedBlock]) -> Document:
        """合并处理后的内容块

        Args:
            blocks: 处理后的内容块列表

        Returns:
            合并后的文档
        """
        # 按位置排序
        sorted_blocks = sorted(blocks, key=lambda x: x.position)

        # 合并内容
        merged_content = "\n\n".join(block.content for block in sorted_blocks)

        # 创建文档对象
        return Document(
            metadata=None,  # TODO: 从前置内容中提取元数据
            blocks=sorted_blocks,
            raw_content=merged_content,
        )
