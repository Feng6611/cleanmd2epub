"""
配置管理模块
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv


class Config:
    """配置管理类"""

    def __init__(self):
        """初始化配置"""
        # 加载环境变量
        load_dotenv()

        # 基础路径
        self.workspace_dir = Path.cwd()
        self.template_dir = self.workspace_dir / "templates"
        self.temp_dir = self.workspace_dir / "temp"
        self.output_dir = self.workspace_dir / "output"
        self.cache_dir = self.workspace_dir / "cache"
        self.assets_dir = self.workspace_dir / "assets"

        # 创建必要的目录
        for dir_path in [
            self.temp_dir,
            self.output_dir,
            self.cache_dir,
            self.assets_dir,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # API 配置
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY 环境变量未设置")

        self.douban_api_key = os.getenv("DOUBAN_API_KEY", "")

        # 缓存配置
        self.cache_enabled = os.getenv("CACHE_ENABLED", "true").lower() == "true"
        try:
            self.cache_ttl = int(os.getenv("CACHE_TTL", "86400"))  # 默认 24 小时
        except ValueError:
            raise ValueError("CACHE_TTL 必须是一个有效的整数")

        # 日志配置
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError("LOG_LEVEL 必须是有效的日志级别")
        self.log_file = self.workspace_dir / "app.log"

        # EPUB 配置
        self.epub_version = "3.0"
        self.default_language = "zh-CN"

        # 文本处理配置
        self.max_block_size = 2000  # 每个块的最大字符数
        self.min_block_size = 500  # 每个块的最小字符数

    def get_api_config(self) -> Dict[str, Any]:
        """获取 API 配置"""
        return {
            "gemini_api_key": self.gemini_api_key,
            "douban_api_key": self.douban_api_key,
        }

    def get_cache_config(self) -> Dict[str, Any]:
        """获取缓存配置"""
        return {
            "enabled": self.cache_enabled,
            "ttl": self.cache_ttl,
            "dir": str(self.cache_dir),  # 转换为字符串以便序列化
        }

    def get_epub_config(self) -> Dict[str, Any]:
        """获取 EPUB 配置"""
        return {
            "version": self.epub_version,
            "language": self.default_language,
        }

    def get_text_config(self) -> Dict[str, Any]:
        """获取文本处理配置"""
        return {
            "max_block_size": self.max_block_size,
            "min_block_size": self.min_block_size,
        }
