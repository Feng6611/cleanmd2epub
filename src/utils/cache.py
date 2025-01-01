"""
缓存管理模块，用于缓存API响应和元数据。
"""

import json
import time
from pathlib import Path
from typing import Any, Optional
from .logger import get_logger

logger = get_logger(__name__)


class Cache:
    def __init__(self, cache_dir: Path, expire_days: int = 7):
        """
        初始化缓存管理器

        Args:
            cache_dir: 缓存目录路径
            expire_days: 缓存过期天数，默认7天
        """
        self.cache_dir = cache_dir
        self.expire_seconds = expire_days * 24 * 60 * 60
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{key}.json"

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存数据

        Args:
            key: 缓存键名

        Returns:
            缓存的数据，如果不存在或已过期则返回None
        """
        cache_path = self._get_cache_path(key)
        if not cache_path.exists():
            return None

        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            # 检查是否过期
            if time.time() - data["timestamp"] > self.expire_seconds:
                logger.debug(f"Cache expired for key: {key}")
                cache_path.unlink()
                return None
            return data["value"]
        except Exception as e:
            logger.error(f"Error reading cache for key {key}: {e}")
            return None

    def set(self, key: str, value: Any) -> bool:
        """
        设置缓存数据

        Args:
            key: 缓存键名
            value: 要缓存的数据

        Returns:
            是否成功设置缓存
        """
        cache_path = self._get_cache_path(key)
        try:
            data = {"timestamp": time.time(), "value": value}
            cache_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            return True
        except Exception as e:
            logger.error(f"Error writing cache for key {key}: {e}")
            return False

    def clear(self, key: Optional[str] = None) -> bool:
        """
        清除缓存

        Args:
            key: 要清除的缓存键名，如果为None则清除所有缓存

        Returns:
            是否成功清除缓存
        """
        try:
            if key:
                cache_path = self._get_cache_path(key)
                if cache_path.exists():
                    cache_path.unlink()
            else:
                for cache_file in self.cache_dir.glob("*.json"):
                    cache_file.unlink()
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False
