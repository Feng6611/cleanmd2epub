import pytest
import pytest_asyncio
from pathlib import Path
import tempfile
import aiofiles
import re

from src.core.document_parser import DocumentParser
from src.interfaces.document_parser import Document, Metadata, ContentBlock
from src.config import Config


@pytest_asyncio.fixture
async def config():
    """测试配置"""
    return Config.from_env()


@pytest_asyncio.fixture
async def cross_cultural_content():
    """《跨文化阅读启示》的测试内容"""
    # 读取原始文件
    with open("跨文化阅读启示 张隆溪.md", "r", encoding="utf-8") as f:
        return f.read()


async def create_temp_file(content: str) -> str:
    """创建临时文件并写入内容"""
    async with aiofiles.tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False
    ) as f:
        await f.write(content)
        return f.name


@pytest.mark.asyncio
async def test_cross_cultural_document_structure(cross_cultural_content, config):
    """测试《跨文化阅读启示》的文档结构"""
    # 创建临时文件
    file_path = await create_temp_file(cross_cultural_content)

    try:
        # 解析文档
        parser = DocumentParser(config)
        doc = await parser.parse_document(file_path)

        # 打印文档结构
        print("\n=== 文档结构 ===")
        print(f"总块数: {len(doc.blocks)}")
        print(
            f"前置内容块数: {len([b for b in doc.blocks if b.block_type == 'frontmatter'])}"
        )
        print(
            f"主体内容块数: {len([b for b in doc.blocks if b.block_type == 'content'])}"
        )

        # 打印详细分块结果
        print("\n=== 详细分块结果 ===")
        for i, block in enumerate(doc.blocks, 1):
            print(f"\n[块 {i}]")
            print(f"类型: {block.block_type}")
            print(f"级别: {block.level}")
            print(f"位置: {block.position}")

            # 获取内容的前三行和最后一行
            lines = block.content.split("\n")
            if len(lines) > 4:
                preview_lines = lines[:3] + ["..."] + [lines[-1]]
            else:
                preview_lines = lines

            print("内容预览:")
            print("-" * 50)
            print("\n".join(preview_lines))
            print("-" * 50)

        # 输出处理结果为 MD 文件
        output_dir = Path("output/test_results")
        output_dir.mkdir(parents=True, exist_ok=True)

        # 输出前置内容
        frontmatter_blocks = [b for b in doc.blocks if b.block_type == "frontmatter"]
        if frontmatter_blocks:
            frontmatter_path = output_dir / "frontmatter.md"
            with open(frontmatter_path, "w", encoding="utf-8") as f:
                f.write(frontmatter_blocks[0].content)

        # 输出主体内容
        content_blocks = [b for b in doc.blocks if b.block_type == "content"]
        if content_blocks:
            content_path = output_dir / "content.md"
            with open(content_path, "w", encoding="utf-8") as f:
                for block in content_blocks:
                    f.write(block.content + "\n\n")

        print("\n=== 输出文件 ===")
        if frontmatter_blocks:
            print(f"前置内容: {frontmatter_path}")
        if content_blocks:
            print(f"主体内容: {content_path}")

        # 基本验证
        assert isinstance(doc, Document)
        assert len(doc.blocks) > 0

        # 验证主体内容
        content_blocks = [b for b in doc.blocks if b.block_type == "content"]
        assert len(content_blocks) > 0

        # 验证总序
        total_preface = next((b for b in content_blocks if "总序" in b.content), None)
        assert total_preface is not None
        assert total_preface.level == 1

    finally:
        # 清理临时文件
        Path(file_path).unlink()
