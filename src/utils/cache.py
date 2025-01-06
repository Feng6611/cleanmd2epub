"""
缓存模块
"""

import json
import time
from pathlib import Path
from typing import Any, Optional
from ..core.config import Config
from .logger import get_logger

logger = get_logger(__name__)


class Cache:
    """缓存管理器"""

    def __init__(self, config: Config):
        """初始化缓存管理器

        Args:
            config: 配置对象
        """
        self.config = config
        self.cache_dir = Path(config.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, key: str) -> Optional[Any]:
        """获取缓存

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在则返回 None
        """
        if not self.config.cache_enabled:
            return None

        cache_file = self.cache_dir / f"{key}.json"
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"读取缓存失败: {e}")
            return None

    def set(self, key: str, value: Any) -> bool:
        """设置缓存

        Args:
            key: 缓存键
            value: 缓存值

        Returns:
            是否成功设置缓存
        """
        if not self.config.cache_enabled:
            return False

        cache_file = self.cache_dir / f"{key}.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(value, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"写入缓存失败: {e}")
            return False

    def exists(self, key: str) -> bool:
        """检查缓存是否存在

        Args:
            key: 缓存键

        Returns:
            是否存在
        """
        if not self.config.cache_enabled:
            return False

        cache_file = self.cache_dir / f"{key}.json"
        return cache_file.exists()

    def clear(self) -> None:
        """清除所有缓存"""
        if not self.cache_dir.exists():
            return

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
            except Exception as e:
                logger.error(f"删除缓存文件失败: {e}")

        logger.info("缓存已清除")
