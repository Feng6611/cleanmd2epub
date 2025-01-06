import asyncio
import pytest
from src.config import Config
from src.core.text_processor import TextProcessor
from src.interfaces.document_parser import ContentBlock


@pytest.mark.asyncio
async def test_basic_workflow():
    """测试基本工作流程"""
    # 初始化配置
    config = Config.from_env()

    # 创建处理器
    processor = TextProcessor(config)

    # 创建测试内容块
    block = ContentBlock(
        content="这是一个测试文本，包含一些OCR错误和格式问题。\n这是第二行。",
        block_type="content",
        level=0,
        position=1,
    )

    # 处理内容块
    processed_block = await processor.process_block(block)

    # 验证结果
    assert processed_block.content != block.content
    assert len(processed_block.content) > 0

    # 验证结果有效性
    is_valid = processor.validate_result(processed_block)
    assert is_valid


if __name__ == "__main__":
    asyncio.run(test_basic_workflow())
