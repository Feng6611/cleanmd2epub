import time
import logging
import asyncio
import google.generativeai as genai
from typing import List, Tuple, Union
from cleanmd import config
import os
from pathlib import Path
from .utils import count_text_length

logger = logging.getLogger(__name__)


class MarkdownCleaner:
    """
    Markdown文本清洗器

    主要职责:
    1. 调用 Gemini API 进行文本清洗
    2. 处理 API 错误和重试
    3. 保存清洗结果
    """

    def __init__(self):
        self._init_gemini_config()
        self.output_dir = os.path.join(config.OUTPUT_DIR, config.CLEANED_DIR)

    def _init_gemini_config(self):
        """初始化 Gemini API 配置"""
        genai.configure(api_key=config.API_KEY)
        generation_config = {
            "temperature": config.TEMPERATURE,
            "top_p": config.TOP_P,
            "top_k": config.TOP_K,
            "max_output_tokens": config.MAX_TOKENS,
        }
        self.model = genai.GenerativeModel(
            config.MODEL, generation_config=generation_config
        )
        self.max_retries = config.MAX_RETRIES
        self.retry_delay = config.RETRY_DELAY

    async def clean_chunk_async(self, context: str, content: str) -> str:
        """
        异步清洗单个文本块

        Args:
            context: 文本块的上下文（前文）
            content: 需要清洗的文本内容

        Returns:
            str: 清洗后的文本
        """
        logger.debug(f"开始清洗文本块，上下文: {context[:50]}...")
        prompts = self._create_prompt(context, content)

        for attempt in range(self.max_retries):
            try:
                logger.debug(f"调用Gemini API (尝试 {attempt + 1}/{self.max_retries})")

                # 创建新的对话
                chat = self.model.start_chat(history=[])

                # 发送系统提示词
                response = await chat.send_message_async(prompts["system"])

                # 发送用户提示词
                response = await chat.send_message_async(prompts["user"])

                if response.text:
                    cleaned_text = response.text.strip()

                    # 打印处理结果
                    print("\n" + "=" * 50)
                    print("清洗结果预览:")
                    print("-" * 50)
                    print(
                        cleaned_text[:500] + "..."
                        if len(cleaned_text) > 500
                        else cleaned_text
                    )
                    print("=" * 50 + "\n")

                    return cleaned_text

            except Exception as e:
                logger.warning(
                    f"API调用失败 (尝试 {attempt + 1}/{self.max_retries}): {str(e)}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error("达到最大重试次数，返回原始内容")
                    return content

        return content

    def _create_prompt(self, context: str, content: str) -> str:
        """
        创建提示词

        Args:
            context: 文本块的上下文
            content: 需要清洗的文本内容

        Returns:
            str: 格式化的提示词
        """
        # 系统提示词：定义AI的角色和行为
        system_prompt = """你是一个专业的学术文本清洗助手。你的任务是清理和优化Markdown文本，同时严格遵守以下规则：
1. 保持原文的核心内容不变
2. 删除所有角标和引用说明
3. 对于引用的文本内容使用 > 标记
4. 保持章节结构和层级关系
5. 直接返回清洗后的文本，不要添加任何解释或说明
6. 保持Markdown格式
"""

        # 用户提示词：具体的任务要求
        user_prompt = f"""请帮我清理和优化以下Markdown文本，重点关注:

1. 段落结构:
- 根据语义和上下文关系重新划分段落
- 合并错误分割的段落
- 分开错误合并的段落
- 保持段落的逻辑连贯性

2. 格式规范:
- 引用文本使用 Markdown 引用格式(>)标记
- 删除所有角标及其解释说明(如 [1]、①、* 等及其对应的引用来源说明)
- 统一标题级别(#、##等)
- 统一段落间距
- 保持列表格式的一致性
- 保持代码块格式(```)

3. 标点符号:
- 修正错误的标点符号
- 补充缺失的标点符号
- 统一中英文标点的使用
- 统一使用半角数字和英文字母
- 确保标点符号前后空格正确

4. 学术规范:
- 保持专业术语的准确性
- 维持学术文本的严谨性
- 不改变原文的核心内容和观点

上下文:
{context}

待清洗文本:
{content}"""

        # 返回完整的提示词
        return {"system": system_prompt, "user": user_prompt}

    async def clean_markdown_async(
        self, chunks: List[Tuple[str, str]], original_path: str
    ) -> str:
        """异步清洗所有文本块"""
        logger.info(f"开始清洗文件: {original_path}")
        cleaned_chunks = []
        total_chunks = len(chunks)

        # 计算总字数用于进度显示
        total_chars = sum(len(content) for _, content in chunks)
        processed_chars = 0

        # 创建临时文件夹存放清洗片段
        temp_dir = Path(self.output_dir) / config.CLEANED_DIR / "chunks"
        temp_dir.mkdir(parents=True, exist_ok=True)

        for i, (context, content) in enumerate(chunks, 1):
            try:
                # 尝试清洗当前片段
                cleaned_chunk = await self._process_chunk(
                    i, total_chunks, context, content, temp_dir
                )
                cleaned_chunks.append(cleaned_chunk)

                # 更新进度
                processed_chars += len(content)
                progress = (processed_chars / total_chars) * 100
                print(f"\n总体进度: {progress:.1f}%")

            except Exception as e:
                logger.error(f"处理第 {i} 个段时出错: {str(e)}")
                cleaned_chunks.append(content)
                print(f"处理出错! 保留原内容")

        # 合并和保存结果
        return self._save_results(cleaned_chunks, original_path, temp_dir, total_chunks)

    async def _process_chunk(
        self,
        chunk_num: int,
        total_chunks: int,
        context: str,
        content: str,
        temp_dir: Path,
    ) -> str:
        """处理单个文本块,支持自动分割过长内容"""
        print(f"\n正在处理第 {chunk_num}/{total_chunks} 个片段...")
        print("-" * 50)
        print(f"上下文: {context[:100]}...")

        try:
            # 首先尝试处理完整片段
            cleaned_chunk = await self.clean_chunk_async(context, content)
            return await self._save_chunk(
                cleaned_chunk, chunk_num, temp_dir, is_split=False
            )

        except Exception as e:
            if "content too long" in str(e).lower():
                logger.warning(f"内容过长,尝试分割处理: {str(e)}")
                return await self._handle_long_chunk(
                    chunk_num, context, content, temp_dir
                )
            raise e

    async def _handle_long_chunk(
        self, chunk_num: int, context: str, content: str, temp_dir: Path
    ) -> str:
        """处理过长的文本块"""
        # 将容分成两半
        mid = len(content) // 2
        # 尝试在段落边界分割
        split_pos = content.rfind("\n\n", 0, mid)
        if split_pos == -1:
            split_pos = mid

        part1 = content[:split_pos]
        part2 = content[split_pos:]

        logger.info(f"将第 {chunk_num} 个片段分割为两部分处理")
        print(f"分割点: {split_pos}/{len(content)} 字符")

        # 处理两个部分
        cleaned_part1 = await self.clean_chunk_async(context, part1)
        cleaned_part1 = await self._save_chunk(
            cleaned_part1, f"{chunk_num}_1", temp_dir, is_split=True
        )

        cleaned_part2 = await self.clean_chunk_async(context + "\n" + part1, part2)
        cleaned_part2 = await self._save_chunk(
            cleaned_part2, f"{chunk_num}_2", temp_dir, is_split=True
        )

        # 合并处理后的部分
        return cleaned_part1 + "\n\n" + cleaned_part2

    async def _save_chunk(
        self,
        content: str,
        chunk_num: Union[int, str],
        temp_dir: Path,
        is_split: bool = False,
    ) -> str:
        """保存处理后的文本块"""
        # 保存当前片段
        chunk_file = temp_dir / f"chunk_{str(chunk_num).zfill(3)}.md"
        chunk_file.write_text(content, encoding="utf-8")

        # 打印处理结果
        print(
            f"{'分块' if is_split else ''}清洗完成! " f"片段大小: {len(content)} 字符"
        )
        print(f"已保存到: {chunk_file}")
        print(f"预览:\n{content[:200]}...")
        print("-" * 50)

        return content

    def _save_results(
        self,
        cleaned_chunks: List[str],
        original_path: str,
        temp_dir: Path,
        total_chunks: int,
    ) -> str:
        """保存最终处理结果"""
        # 合并所有片段
        cleaned_content = "\n\n".join(chunk for chunk in cleaned_chunks if chunk)

        # 保存最终结果
        output_path = self.save_cleaned_content(original_path, cleaned_content)
        logger.info(f"文件清洗完成，已保存到: {output_path}")

        # 打印最终统计
        print("\n清洗完成!")
        print(f"- 总片段数: {total_chunks}")
        print(f"- 清洗后大小: {len(cleaned_content)} 字")
        print(f"- 最终文件: {output_path}")
        print(f"- 片段文件夹: {temp_dir}")

        return output_path

    def save_cleaned_content(self, original_path: str, cleaned_content: str) -> str:
        """保存清洗后的内容"""
        original_path = Path(original_path)
        filename = original_path.stem + config.OUTPUT_SUFFIX + original_path.suffix
        output_path = Path(self.output_dir) / filename

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(cleaned_content, encoding="utf-8")

        return str(output_path)

    def _check_chunk_size(self, chunk: str) -> bool:
        """
        检查文本块大小是否在允许范围内

        Args:
            chunk: 文本块内容

        Returns:
            bool: 是否在允许范围内
        """
        length = count_text_length(chunk)
        return config.MIN_CHUNK_SIZE <= length <= config.MAX_CHUNK_SIZE
