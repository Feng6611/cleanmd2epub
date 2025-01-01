"""
日志工具模块
"""

import logging


def get_logger(name: str) -> logging.Logger:
    """获取日志记录器"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # 如果没有处理器，添加一个
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
