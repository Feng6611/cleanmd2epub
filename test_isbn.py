"""
测试豆瓣爬虫获取图书元数据
"""

import asyncio
from pathlib import Path
from src.core.config import Config
from src.utils.douban_crawler import DoubanCrawler
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def main():
    # 初始化配置和爬虫
    config = Config(
        cache_dir=str(Path.home() / ".cache/cleanmd2epub"),
        api_key="test_key",  # 豆瓣爬虫不需要 API key，但配置类要求这个字段
    )
    crawler = DoubanCrawler(config)

    # 测试 ISBN (新的测试图书)
    isbn = "9787513946933"
    logger.info(f"正在获取 ISBN {isbn} 的图书信息...")

    # 获取页面内容
    url = f"https://book.douban.com/isbn/{isbn}/"
    content = await crawler._fetch_url(url)
    if content:
        logger.info("页面内容获取成功，正在解析...")
        logger.debug(f"页面内容：\n{content[:1000]}...")  # 只显示前1000个字符

        # 测试各个提取函数
        title = crawler._extract_title(content)
        author = crawler._extract_author(content)
        douban_id = crawler._extract_douban_id(content)

        logger.info(f"提取结果：")
        logger.info(f"标题: {title}")
        logger.info(f"作者: {author}")
        logger.info(f"豆瓣ID: {douban_id}")

        metadata = await crawler.get_book_metadata(isbn)
        if metadata:
            logger.info("元数据获取成功！图书信息如下：")
            for key, value in metadata.items():
                logger.info(f"{key}: {value}")
        else:
            logger.error("元数据获取失败！")
    else:
        logger.error("页面内容获取失败！")


if __name__ == "__main__":
    asyncio.run(main())
