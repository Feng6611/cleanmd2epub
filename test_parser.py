import asyncio
from src.core.document_parser import DocumentParser
from src.core.config import Config


async def main():
    config = Config()  # 使用默认配置
    parser = DocumentParser(config)

    # 解析文档
    document = await parser.parse_document("跨文化阅读启示 张隆溪.md")

    # 打印解析结果
    print(f"文档解析完成，共有 {len(document.blocks)} 个内容块")

    for i, block in enumerate(document.blocks, 1):
        print(f"\n=== 块 {i} ===")
        print(f"类型: {block.block_type}")
        print(f"级别: {block.level}")
        print(f"位置: {block.position}")
        content_len = len(block.content)
        weighted_len = parser._count_chars(block.content)
        print(f"内容长度: {content_len} 字符")
        print(f"加权长度: {weighted_len} (中文2/英文1)")

        print("\n内容预览:")
        preview = (
            block.content[:200] + "..." if len(block.content) > 200 else block.content
        )
        print(preview)
        print("-" * 80)


if __name__ == "__main__":
    asyncio.run(main())
