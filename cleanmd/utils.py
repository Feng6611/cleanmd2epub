import re
import logging
from functools import wraps
from typing import Callable, Any, Union

logger = logging.getLogger(__name__)


def log_operation(operation: str) -> Callable:
    """日志装饰器

    Args:
        operation: 操作描述

    Returns:
        装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            logger.info(f"开始{operation}")
            try:
                result = await func(*args, **kwargs)
                logger.info(f"{operation}完成")
                return result
            except Exception as e:
                logger.error(f"{operation}失败: {str(e)}")
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            logger.info(f"开始{operation}")
            try:
                result = func(*args, **kwargs)
                logger.info(f"{operation}完成")
                return result
            except Exception as e:
                logger.error(f"{operation}失败: {str(e)}")
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def count_text_length(text: str) -> int:
    """计算文本长度

    Args:
        text: 输入文本

    Returns:
        文本长度(中文字符计2,其他字符计1)
    """
    # 移除Markdown标记
    markdown_pattern = r"(?<!\\)([*_~`#>|\[\]\(\)\{\}]|^#+ )"
    clean_text = re.sub(markdown_pattern, "", text)

    # 计算中文字符(每个计2)
    chinese_pattern = r"[\u4e00-\u9fff]"
    chinese_chars = re.findall(chinese_pattern, clean_text)
    chinese_length = len(chinese_chars) * 2

    # 计算其他字符(每个计1)
    remaining_text = re.sub(chinese_pattern, "", clean_text)
    other_length = len("".join(c for c in remaining_text if c.strip()))

    return chinese_length + other_length


class ProgressBar:
    """进度条显示类"""

    def __init__(self, total: int, prefix: str = "", suffix: str = ""):
        self.total = total
        self.prefix = prefix
        self.suffix = suffix
        self.current = 0

    def update(self, n: int = 1):
        """更新进度"""
        self.current += n
        percent = 100 * (self.current / float(self.total))
        bar = "=" * int(percent / 2) + "-" * (50 - int(percent / 2))
        print(f"\r{self.prefix} |{bar}| {percent:.1f}% {self.suffix}", end="\r")
        if self.current == self.total:
            print()
