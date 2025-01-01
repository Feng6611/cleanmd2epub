"""
配置管理模块
"""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import ConfigDict


class Config(BaseSettings):
    """应用配置类"""

    # API 配置
    api_key: str
    api_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    api_model: str = "gemini-pro"
    api_timeout: int = 30

    # 缓存配置
    cache_dir: str = str(Path.home() / ".cache" / "cleanmd2epub")
    cache_expire_days: int = 7

    # 文档处理配置
    max_block_size: int = 1000  # 每个文本块的最大字符数
    max_retries: int = 3  # API 调用最大重试次数
    retry_delay: int = 1  # 重试间隔（秒）

    # 输出配置
    output_dir: str = "output"
    template_dir: str = "templates"

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",  # 允许额外字段
    )
