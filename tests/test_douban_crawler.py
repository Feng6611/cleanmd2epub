"""
豆瓣爬虫测试模块
"""

import pytest
import asyncio
from pathlib import Path
from typing import Optional
from src.core.config import Config
from src.utils.douban_crawler import DoubanCrawler
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Mock HTML 响应
MOCK_BOOK_HTML = """
<div id="wrapper">
    <h1><span property="v:itemreviewed">三体</span></h1>
    <div id="info">
        <span>作者</span>: <a href="/author/1">刘慈欣</a><br/>
        出版社:</span> 重庆出版社<br/>
        出版年:</span> 2008-1<br/>
    </div>
    <div class="rating_wrap">
        <div class="rating_num">9.3</div>
    </div>
    <div id="mainpic">
        <img src="https://img1.doubanio.com/view/subject/l/public/s2768378.jpg" title="点击看大图"/>
    </div>
    <div class="intro">
        <p>文化大革命如火如荼进行的同时，军方探寻外星文明的绝秘计划"红岸工程"取得了突破性进展...</p>
    </div>
    <div class="subject-id">
        <a href="https://book.douban.com/subject/2567698/">豆瓣链接</a>
    </div>
</div>
"""


@pytest.fixture
def config():
    return Config(
        cache_dir=str(Path(__file__).parent / "test_cache"), api_key="test_key"
    )


@pytest.fixture
def crawler(config):
    return DoubanCrawler(config)


@pytest.fixture(autouse=True)
def mock_responses(monkeypatch):
    async def mock_fetch_url(self, url: str) -> Optional[str]:
        logger.debug(f"Mock fetch URL: {url}")
        if "9787536692930" in url:
            logger.debug("Returning book details")
            return MOCK_BOOK_HTML
        logger.debug("Returning None for invalid ISBN or unknown URL")
        return None

    monkeypatch.setattr(DoubanCrawler, "_fetch_url", mock_fetch_url)


@pytest.mark.asyncio
async def test_get_book_metadata(crawler):
    # 测试获取《三体》的元数据
    isbn = "9787536692930"
    metadata = await crawler.get_book_metadata(isbn)

    assert metadata is not None
    assert metadata["isbn"] == isbn
    assert metadata["title"] == "三体"
    assert "刘慈欣" in metadata["author"]
    assert metadata["publisher"] == "重庆出版社"
    assert metadata["rating"] == 9.3
    assert (
        metadata["cover_url"]
        == "https://img1.doubanio.com/view/subject/l/public/s2768378.jpg"
    )
    assert "文化大革命" in metadata["description"]
    assert metadata["douban_id"] == "2567698"


@pytest.mark.asyncio
async def test_get_book_metadata_invalid_isbn(crawler):
    # 测试无效的ISBN
    isbn = "invalid_isbn"
    metadata = await crawler.get_book_metadata(isbn)
    assert metadata is None


@pytest.mark.asyncio
async def test_get_book_metadata_cache(crawler):
    # 测试缓存功能
    isbn = "9787536692930"

    # 第一次调用，从网络获取
    metadata1 = await crawler.get_book_metadata(isbn)
    assert metadata1 is not None

    # 第二次调用，应该从缓存获取
    metadata2 = await crawler.get_book_metadata(isbn)
    assert metadata2 is not None
    assert metadata1 == metadata2  # 两次结果应该完全相同


@pytest.mark.asyncio
async def test_fetch_url(crawler):
    # 测试URL获取
    url = "https://book.douban.com/isbn/9787536692930/"
    content = await crawler._fetch_url(url)
    assert content == MOCK_BOOK_HTML

    # 测试无效URL
    url = "https://book.douban.com/isbn/invalid_isbn/"
    content = await crawler._fetch_url(url)
    assert content is None
