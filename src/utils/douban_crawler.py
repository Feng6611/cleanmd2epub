"""
豆瓣元数据爬虫模块，用于获取图书的基本信息。
"""

import re
import json
import asyncio
import aiohttp
import random
from typing import Optional, Dict, Any
from pathlib import Path
from ..core.config import Config
from .logger import get_logger
from .cache import Cache

logger = get_logger(__name__)


class DoubanCrawler:
    """豆瓣图书爬虫"""

    def __init__(self, config: Config):
        """初始化爬虫

        Args:
            config: 配置对象
        """
        self.config = config
        self.cache = Cache(Path(config.cache_dir) / "metadata")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

    async def _fetch_url(self, url: str) -> Optional[str]:
        """获取URL内容"""
        try:
            # 随机延迟 1-3 秒
            await asyncio.sleep(random.uniform(1, 3))

            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.text()
                    logger.warning(f"Failed to fetch {url}, status: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    async def get_book_metadata(self, isbn: str) -> Optional[Dict[str, Any]]:
        """获取图书元数据

        Args:
            isbn: 图书的ISBN

        Returns:
            图书元数据字典，如果获取失败则返回 None
        """
        # 检查缓存
        cache_key = f"metadata_{isbn}"
        if cached := self.cache.get(cache_key):
            logger.debug(f"Using cached metadata for ISBN: {isbn}")
            return cached

        # 直接访问 ISBN 对应的页面
        url = f"https://book.douban.com/isbn/{isbn}/"
        logger.debug(f"Fetching metadata for ISBN: {isbn} from {url}")

        content = await self._fetch_url(url)
        if not content:
            logger.warning(f"Failed to fetch content for ISBN: {isbn}")
            return None

        # 解析HTML获取元数据
        try:
            # 先检查是否有必要的字段
            title = self._extract_title(content)
            author = self._extract_author(content)
            if not title or not author:
                logger.error(f"Missing required metadata fields for ISBN {isbn}")
                return None

            # 提取豆瓣ID
            douban_id = self._extract_douban_id(content)
            if not douban_id:
                logger.error(f"Failed to extract Douban ID for ISBN {isbn}")
                return None

            metadata = {
                "isbn": isbn,
                "douban_id": douban_id,
                "title": title,
                "author": author,
                "publisher": self._extract_publisher(content),
                "publish_date": self._extract_publish_date(content),
                "rating": self._extract_rating(content),
                "cover_url": self._extract_cover_url(content),
                "description": self._extract_description(content),
            }

            # 缓存结果
            self.cache.set(cache_key, metadata)
            logger.debug(f"Successfully fetched metadata for ISBN: {isbn}")
            return metadata
        except Exception as e:
            logger.error(f"Error parsing metadata for ISBN {isbn}: {e}")
            return None

    def _extract_douban_id(self, content: str) -> Optional[str]:
        """从页面内容中提取豆瓣ID"""
        pattern = r"https://book.douban.com/subject/(\d+)/"
        if match := re.search(pattern, content):
            return match.group(1)
        return None

    def _extract_title(self, content: str) -> str:
        """提取书名"""
        patterns = [
            r"<title>(.*?)(?:\(豆瓣\))?</title>",  # 从标题标签中提取
            r"<h1>\s*<span[^>]*>([^<]+)</span>\s*</h1>",  # 从 h1 标签中提取
            r'property="v:itemreviewed"[^>]*>([^<]+)<',  # 从元数据中提取
        ]
        for pattern in patterns:
            if match := re.search(pattern, content):
                return match.group(1).strip()
        return ""

    def _extract_author(self, content: str) -> str:
        """提取作者"""
        patterns = [
            r"作者</span>:?\s*<a[^>]*>([^<]+)</a>",  # 链接形式
            r"作者</span>:?\s*([^<]+)<",  # 纯文本形式
            r"作者:([^<]+)<",  # 简单形式
        ]
        for pattern in patterns:
            if match := re.search(pattern, content):
                return match.group(1).strip()
        return ""

    def _extract_publisher(self, content: str) -> str:
        """提取出版社"""
        patterns = [
            r"出版社:</span>\s*<a[^>]*>([^<]+)</a>",  # 链接形式
            r"出版社:</span>\s*([^<]+)<",  # 纯文本形式
            r"出版社:([^<]+)<",  # 简单形式
        ]
        for pattern in patterns:
            if match := re.search(pattern, content):
                return match.group(1).strip()
        return ""

    def _extract_publish_date(self, content: str) -> str:
        """提取出版日期"""
        patterns = [
            r"出版年:</span>\s*<a[^>]*>([^<]+)</a>",  # 链接形式
            r"出版年:</span>\s*([^<]+)<",  # 纯文本形式
            r"出版年:([^<]+)<",  # 简单形式
        ]
        for pattern in patterns:
            if match := re.search(pattern, content):
                return match.group(1).strip()
        return ""

    def _extract_rating(self, content: str) -> float:
        """提取评分"""
        patterns = [
            r"rating_num[^>]*>([^<]+)<",  # 标准形式
            r'property="v:average"[^>]*>([^<]+)<',  # 元数据形式
            r"rating_nums[^>]*>([^<]+)<",  # 旧版形式
        ]
        for pattern in patterns:
            if match := re.search(pattern, content):
                try:
                    return float(match.group(1).strip())
                except ValueError:
                    continue
        return 0.0

    def _extract_cover_url(self, content: str) -> str:
        """提取封面URL"""
        patterns = [
            r'<img[^>]*src="([^"]+)"[^>]*title="点击看大图"',  # 标准形式
            r'property="og:image"[^>]*content="([^"]+)"',  # 元数据形式
            r'<img[^>]*src="([^"]+)"[^>]*class="[^"]*cover[^"]*"',  # 封面类形式
        ]
        for pattern in patterns:
            if match := re.search(pattern, content):
                return match.group(1)
        return ""

    def _extract_description(self, content: str) -> str:
        """提取图书简介"""
        patterns = [
            r'<div class="intro">\s*<p>([^<]+)</p>',  # 标准形式
            r'property="v:summary"[^>]*>([^<]+)<',  # 元数据形式
            r'class="book-intro"[^>]*>([^<]+)<',  # 简单形式
        ]
        for pattern in patterns:
            if match := re.search(pattern, content):
                return match.group(1).strip()
        return ""
