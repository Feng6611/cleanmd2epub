import asyncio
from typing import List, Optional, Dict, Any
import google.generativeai as genai
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
    after_log,
)
import logging
import json
from pathlib import Path

from ..interfaces.text_processor import ITextProcessor
from ..interfaces.document_parser import Document, ContentBlock, Metadata
from ..config import Config
from ..utils.logger import get_logger
from ..utils.cache import Cache
from .prompts import SYSTEM_PROMPTS, USER_PROMPTS

logger = get_logger(__name__)


class TextProcessor(ITextProcessor):
    """文本处理器实现类"""

    def __init__(self, config: Config):
        """初始化文本处理器

        Args:
            config: 配置对象
        """
        self.config = config
        self.cache = Cache(config)

        # 初始化 Gemini 模型
        genai.configure(api_key=config.gemini_api_key)
        generation_config = {
            "temperature": config.gemini_temperature,
            "top_p": config.gemini_top_p,
            "top_k": config.gemini_top_k,
            "max_output_tokens": config.gemini_max_output_tokens,
            "stop_sequences": config.gemini_stop_sequences,
        }

        # 设置安全级别
        safety_settings = [
            {
                "category": genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                "threshold": genai.types.HarmBlockThreshold.BLOCK_NONE,
            },
            {
                "category": genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                "threshold": genai.types.HarmBlockThreshold.BLOCK_NONE,
            },
            {
                "category": genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                "threshold": genai.types.HarmBlockThreshold.BLOCK_NONE,
            },
            {
                "category": genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                "threshold": genai.types.HarmBlockThreshold.BLOCK_NONE,
            },
        ]

        self.model = genai.GenerativeModel(
            model_name="gemini-pro",
            generation_config=generation_config,
            safety_settings=safety_settings,
        )

    async def _call_model(
        self, system_prompt: str, user_prompt: str, timeout: Optional[float] = None
    ) -> Optional[str]:
        """调用 Gemini 模型

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            timeout: 超时时间（秒）

        Returns:
            模型响应文本，如果失败则返回 None
        """
        try:
            # 添加请求延时
            await asyncio.sleep(self.config.gemini_retry_delay)

            # 组合提示词
            combined_prompt = f"{system_prompt}\n\n{user_prompt}"

            # 设置超时
            timeout = timeout or self.config.gemini_timeout
            response = await asyncio.wait_for(
                self.model.generate_content_async(combined_prompt),
                timeout=timeout,
            )

            if not response or not response.text:
                logger.warning("Empty response from API")
                return None

            return response.text.strip()

        except asyncio.TimeoutError:
            logger.error("API request timed out")
            raise
        except Exception as e:
            logger.error(f"Failed to call model: {e}")
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=30, min=30, max=120),
        before_sleep=before_sleep_log(logger, log_level=logging.INFO),
        after=after_log(logger, log_level=logging.INFO),
    )
    async def _extract_metadata(self, block: ContentBlock) -> Optional[Metadata]:
        """从前置内容中提取元数据

        Args:
            block: 前置内容块

        Returns:
            元数据对象
        """
        try:
            # 获取提示词
            system_prompt = SYSTEM_PROMPTS["metadata_extractor"]
            user_prompt = USER_PROMPTS["metadata_extraction"].format(
                content=block.content
            )

            # 调用模型
            response = await self._call_model(system_prompt, user_prompt)
            if not response:
                return None

            # 查找第一个 { 和最后一个 } 的位置
            start = response.find("{")
            end = response.rfind("}")

            if start == -1 or end == -1:
                logger.error(f"Invalid JSON response: {response}")
                return None

            # 提取 JSON 部分
            json_text = response[start : end + 1]

            # 解析 JSON 响应
            metadata_dict = json.loads(json_text)

            # 确保只使用 Metadata 类支持的字段
            valid_fields = {"title", "author", "publisher", "isbn", "description"}
            filtered_dict = {
                k: v for k, v in metadata_dict.items() if k in valid_fields
            }

            return Metadata(**filtered_dict)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse metadata JSON: {e}")
            logger.debug(f"Raw response: {response}")
            return None
        except Exception as e:
            logger.error(f"Failed to extract metadata: {e}")
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=30, min=30, max=120),
        before_sleep=before_sleep_log(logger, log_level=logging.INFO),
        after=after_log(logger, log_level=logging.INFO),
    )
    async def _process_content(self, content: str) -> Optional[str]:
        """处理文本内容

        Args:
            content: 原始文本内容

        Returns:
            处理后的文本内容，如果处理失败则返回 None
        """
        try:
            # 获取提示词
            system_prompt = SYSTEM_PROMPTS["content_processor"]
            user_prompt = USER_PROMPTS["content_processing"].format(content=content)

            # 调用模型
            processed_content = await self._call_model(system_prompt, user_prompt)
            if not processed_content:
                return None

            # 验证结果
            if not self.validate_result(processed_content):
                logger.warning("Invalid result from API")
                return None

            return processed_content

        except Exception as e:
            logger.error(f"Failed to process content: {e}")
            return None

    def validate_result(self, content: str | ContentBlock) -> bool:
        """验证处理结果

        Args:
            content: 处理后的内容或内容块

        Returns:
            是否有效
        """
        if isinstance(content, ContentBlock):
            content = content.content

        if not content:
            return False

        # 检查内容长度
        if len(content.strip()) < 10:
            return False

        # 检查是否包含基本标点
        if not any(p in content for p in "。，、；：？！"):
            return False

        return True

    async def process_block(self, block: ContentBlock) -> Optional[ContentBlock]:
        """处理单个内容块

        Args:
            block: 内容块

        Returns:
            处理后的内容块，如果处理失败则返回 None
        """
        # 检查缓存
        cache_key = f"block_{hash(block.content)}"
        cached_data = self.cache.get(cache_key)
        if cached_data:
            try:
                return ContentBlock.from_dict(cached_data)
            except Exception as e:
                logger.error(f"从缓存恢复内容块失败: {e}")

        try:
            # 根据块类型选择不同的处理方式
            if block.block_type == "frontmatter":
                system_prompt = SYSTEM_PROMPTS["frontmatter_processor"]
                user_prompt = USER_PROMPTS["frontmatter_processing"].format(
                    content=block.content
                )
            else:
                system_prompt = SYSTEM_PROMPTS["content_processor"]
                user_prompt = USER_PROMPTS["content_processing"].format(
                    content=block.content
                )

            # 处理内容
            processed_content = await self._call_model(system_prompt, user_prompt)
            if not processed_content:
                return None

            # 创建新的内容块
            processed_block = ContentBlock(
                content=processed_content,
                block_type=block.block_type,
                level=block.level,
                position=block.position,
            )

            # 缓存结果
            self.cache.set(cache_key, processed_block.to_dict())

            return processed_block

        except Exception as e:
            logger.error(f"处理内容块时出错: {e}")
            return None

    async def process_document(self, document: Document) -> Document:
        """处理整个文档

        Args:
            document: 原始文档

        Returns:
            处理后的文档
        """
        processed_blocks = []
        logger.info("开始处理文档...")

        # 1. 首先处理前置内容并提取元数据
        frontmatter = next(
            (block for block in document.blocks if block.block_type == "frontmatter"),
            None,
        )

        if frontmatter:
            try:
                logger.debug("开始处理前置内容...")
                # 提取元数据
                metadata = await self._extract_metadata(frontmatter)
                if metadata:
                    logger.info(f"成功提取元数据: {metadata}")
                    document.metadata = metadata
                else:
                    logger.warning("未能提取到元数据")

                # 处理前置内容
                processed_frontmatter = await self.process_block(frontmatter)
                if processed_frontmatter:
                    processed_blocks.append(processed_frontmatter)
                    logger.debug("前置内容处理完成")
                else:
                    logger.warning("前置内容处理失败，使用原始内容")
                    processed_blocks.append(frontmatter)
            except Exception as e:
                logger.error(f"处理前置内容时出错: {str(e)}")
                processed_blocks.append(frontmatter)  # 保留原始内容
        else:
            logger.warning("未找到前置内容")

        # 2. 处理主体内容块
        content_blocks = [b for b in document.blocks if b.block_type != "frontmatter"]
        logger.info(f"开始处理 {len(content_blocks)} 个主体内容块...")

        for i, block in enumerate(content_blocks, 1):
            try:
                logger.debug(f"处理第 {i}/{len(content_blocks)} 个内容块...")
                processed_block = await self.process_block(block)
                if processed_block:
                    processed_blocks.append(processed_block)
                    logger.debug(f"第 {i} 个内容块处理完成")
                else:
                    logger.warning(f"第 {i} 个内容块处理失败，使用原始内容")
                    processed_blocks.append(block)
            except Exception as e:
                logger.error(f"处理第 {i} 个内容块时出错: {str(e)}")
                processed_blocks.append(block)  # 保留原始内容

        # 3. 按原始位置排序所有块
        processed_blocks.sort(key=lambda x: x.position)

        # 4. 更新文档
        document.blocks = processed_blocks
        logger.info(f"文档处理完成，共处理 {len(processed_blocks)} 个内容块")

        # 5. 验证处理结果
        if not processed_blocks:
            logger.error("处理后的文档为空")
            return document

        # 检查是否包含前置内容
        has_frontmatter = any(
            block.block_type == "frontmatter" for block in processed_blocks
        )
        if not has_frontmatter:
            logger.warning("处理后的文档不包含前置内容")

        return document

    def merge_blocks(self, blocks: List[ContentBlock]) -> Document:
        """合并内容块

        Args:
            blocks: 内容块列表

        Returns:
            合并后的文档
        """
        # 按位置排序
        blocks.sort(key=lambda x: x.position)

        # 合并内容
        content = "\n\n".join(block.content for block in blocks)

        return Document(blocks=blocks, raw_content=content)
