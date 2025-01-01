import pytest
import pytest_asyncio
from unittest.mock import Mock, patch
from src.core.text_processor import TextProcessor
from src.interfaces.document_parser import ContentBlock, Document, Metadata
from src.interfaces.text_processor import ProcessedBlock
from src.config import Config


@pytest_asyncio.fixture
async def config():
    """测试配置"""
    return Config(gemini_api_key="test_key", enable_cache=False)


@pytest_asyncio.fixture
async def text_processor(config):
    """文本处理器实例"""
    return TextProcessor(config)


@pytest_asyncio.fixture
async def content_block():
    """测试用内容块"""
    return ContentBlock(
        content="这是一个测试文本，包含一些OCR错误和格式问题。\n这是第二行。",
        block_type="content",
        level=0,
        position=1,
    )


@pytest.mark.asyncio
async def test_process_block(text_processor, content_block):
    """测试处理单个内容块"""
    # Mock Gemini API 响应
    mock_response = Mock()
    mock_response.text = "这是处理后的文本。\n这是第二行。"

    with patch.object(
        text_processor.model, "generate_content_async", return_value=mock_response
    ):
        result = await text_processor.process_block(content_block)

        assert result.content == mock_response.text
        assert result.original_content == content_block.content
        assert result.block_type == content_block.block_type
        assert result.level == content_block.level
        assert result.position == content_block.position


@pytest.mark.asyncio
async def test_validate_result(text_processor, content_block):
    """测试验证处理结果"""
    # Mock Gemini API 响应
    mock_response = Mock()
    mock_response.text = "这是处理后的文本。\n这是第二行。"

    with patch.object(
        text_processor.model, "generate_content_async", return_value=mock_response
    ):
        processed_block = await text_processor.process_block(content_block)
        is_valid = await text_processor.validate_result(processed_block)
        assert isinstance(is_valid, bool)


@pytest.mark.asyncio
async def test_merge_blocks(text_processor):
    """测试合并内容块"""
    blocks = [
        ContentBlock(content="第一块", block_type="content", level=0, position=1),
        ContentBlock(content="第二块", block_type="content", level=0, position=2),
    ]

    # Mock process_block
    async def mock_process_block(block):
        return ProcessedBlock(
            content=f"处理后的{block.content}",
            block_type=block.block_type,
            level=block.level,
            position=block.position,
            original_content=block.content,
            changes_made=[],
            confidence_score=1.0,
        )

    with patch.object(text_processor, "process_block", side_effect=mock_process_block):
        processed_blocks = [
            await text_processor.process_block(block) for block in blocks
        ]

        result = await text_processor.merge_blocks(processed_blocks)

        assert isinstance(result, Document)
        assert len(result.blocks) == 2
        assert result.blocks[0].position < result.blocks[1].position


@pytest.mark.asyncio
async def test_cache_mechanism(text_processor, content_block):
    """测试缓存机制"""
    # 启用缓存
    text_processor.config.enable_cache = True

    # Mock Gemini API 响应
    mock_response = Mock()
    mock_response.text = "这是处理后的文本"

    with patch.object(
        text_processor.model, "generate_content_async", return_value=mock_response
    ) as mock_generate:
        # 第一次调用
        result1 = await text_processor.process_block(content_block)
        # 第二次调用相同内容
        result2 = await text_processor.process_block(content_block)

        # 验证 API 只被调用一次
        assert mock_generate.call_count == 1
        # 验证两次结果相同
        assert result1.content == result2.content


@pytest.mark.asyncio
async def test_retry_mechanism(text_processor, content_block):
    """测试重试机制"""
    # Mock 一个会失败两次然后成功的 API 调用
    mock_response = Mock()
    mock_response.text = "这是处理后的文本"

    call_count = 0

    async def mock_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("API 调用失败")
        return mock_response

    with patch.object(
        text_processor.model, "generate_content_async", side_effect=mock_generate
    ):
        result = await text_processor.process_block(content_block)

        assert call_count == 3  # 验证重试了两次后成功
        assert result.content == mock_response.text
