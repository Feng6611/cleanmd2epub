from dataclasses import dataclass
from typing import Optional
import os
from dotenv import load_dotenv

from .utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Config:
    """配置类"""

    # Gemini API 配置
    gemini_api_key: str
    gemini_max_retries: int = 3
    gemini_retry_delay: int = 1
    gemini_timeout: int = 30

    # 缓存配置
    enable_cache: bool = True
    cache_dir: Optional[str] = None

    # 处理配置
    max_block_size: int = 1000  # 每个块的最大字符数
    min_block_size: int = 100  # 每个块的最小字符数

    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量加载配置

        Returns:
            Config对象
        """
        load_dotenv()

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("未设置 GEMINI_API_KEY 环境变量")

        return cls(
            gemini_api_key=api_key,
            gemini_max_retries=int(os.getenv("GEMINI_MAX_RETRIES", "3")),
            gemini_retry_delay=int(os.getenv("GEMINI_RETRY_DELAY", "1")),
            gemini_timeout=int(os.getenv("GEMINI_TIMEOUT", "30")),
            enable_cache=os.getenv("ENABLE_CACHE", "true").lower() == "true",
            cache_dir=os.getenv("CACHE_DIR"),
            max_block_size=int(os.getenv("MAX_BLOCK_SIZE", "1000")),
            min_block_size=int(os.getenv("MIN_BLOCK_SIZE", "100")),
        )
