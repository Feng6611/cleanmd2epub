from pathlib import Path
from typing import Optional, List, Dict
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """配置类"""

    # Gemini API 配置
    gemini_api_key: str
    gemini_max_retries: int = 3  # 最大重试次数
    gemini_retry_delay: int = 15  # 每次请求的延时(秒)
    gemini_timeout: int = 30  # 请求超时时间(秒)
    gemini_max_backoff: int = 120  # 最大退避时间(秒)
    gemini_temperature: float = 0.5  # 生成温度
    gemini_top_p: float = 0.8  # 采样阈值
    gemini_top_k: int = 40  # 采样数量
    gemini_max_output_tokens: int = 2048  # 最大输出长度
    gemini_stop_sequences: List[str] = []  # 停止序列

    # 缓存配置
    cache_enabled: bool = True
    cache_ttl: int = 86400  # 24小时
    cache_dir: Path = Path(".cache")

    # 日志配置
    log_level: str = "INFO"

    # 重试配置
    max_retries: int = 3
    retry_delay: int = 1

    # 文档处理配置
    max_block_size: int = 6000
    min_block_size: int = 4000

    # EPUB 生成配置
    template_dir: Path = Path("templates")
    temp_dir: Path = Path(".temp")
    output_dir: Path = Path("output")
    assets_dir: Path = Path("assets")  # 用于存储封面图片等资源
    default_cover: Path = Path("assets/default_cover.jpg")  # 默认封面图片
    cover_width: int = 1400  # 封面图片宽度
    cover_height: int = 2100  # 封面图片高度（A5 比例）
    cover_font: str = "Noto Serif CJK SC"  # 封面字体
    cover_font_size: int = 48  # 封面字体大小
    cover_background: str = "#FFFFFF"  # 封面背景色
    cover_text_color: str = "#000000"  # 封面文字颜色

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量创建配置对象"""
        config = cls()
        return config
