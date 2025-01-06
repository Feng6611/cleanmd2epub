from src.core.document_parser import DocumentParser
from src.config import Config
from src.interfaces.document_parser import Document
import asyncio


async def main():
    parser = DocumentParser(Config())
    await parser.parse_document("跨文化阅读启示 张隆溪_final.md")


if __name__ == "__main__":
    asyncio.run(main())
