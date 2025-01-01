import os
from pathlib import Path
from typing import List, Tuple

from .logger import get_logger

logger = get_logger(__name__)


def read_markdown_file(file_path: str) -> str:
    """读取 Markdown 文件

    Args:
        file_path: 文件路径

    Returns:
        文件内容
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"读取文件失败: {str(e)}")
        raise


def write_markdown_file(file_path: str, content: str) -> None:
    """写入 Markdown 文件

    Args:
        file_path: 文件路径
        content: 文件内容
    """
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        logger.error(f"写入文件失败: {str(e)}")
        raise


def ensure_dir(dir_path: str) -> None:
    """确保目录存在

    Args:
        dir_path: 目录路径
    """
    try:
        os.makedirs(dir_path, exist_ok=True)
    except Exception as e:
        logger.error(f"创建目录失败: {str(e)}")
        raise


def get_file_size(file_path: str) -> int:
    """获取文件大小

    Args:
        file_path: 文件路径

    Returns:
        文件大小（字节）
    """
    try:
        return os.path.getsize(file_path)
    except Exception as e:
        logger.error(f"获取文件大小失败: {str(e)}")
        raise
