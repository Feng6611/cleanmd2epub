import asyncio
import pytest
from src.core.document_parser import DocumentParser
from src.config import Config
from pprint import pprint


@pytest.mark.asyncio
async def test_actual_book():
    """测试实际书籍文件的处理结果"""
    config = Config.from_env()
    parser = DocumentParser(config)
    doc = await parser.parse_document("跨文化阅读启示 张隆溪.md")

    print("\n=== 元数据 ===")
    print(f"标题: {doc.metadata.title}")
    print(f"作者: {doc.metadata.author}")
    print(f"ISBN: {doc.metadata.isbn}")
    print(f"出版社: {doc.metadata.publisher}")
    print(f"描述: {doc.metadata.description}")

    print("\n=== 前置部分 ===")
    frontmatter_block = next(
        (block for block in doc.blocks if block.block_type == "frontmatter"), None
    )
    if frontmatter_block:
        print(frontmatter_block.content)
    else:
        print("未找到前置部分")

    print("\n=== 内容块 ===")
    for i, block in enumerate(doc.blocks):
        if block.block_type != "frontmatter":  # 只显示非前置部分的块
            print(f"\n--- 块 {i+1} ---")
            print(f"类型: {block.block_type}")
            print(f"级别: {block.level}")
            print(f"位置: {block.position}")
            # 显示内容的前两行和最后一行
            lines = block.content.split("\n")
            preview = (
                lines[:2]
                + (["..."] if len(lines) > 3 else [])
                + ([lines[-1]] if len(lines) > 2 else [])
            )
            print("内容预览:")
            print("\n".join(preview))


if __name__ == "__main__":
    asyncio.run(test_actual_book())
