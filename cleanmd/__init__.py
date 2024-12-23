"""
Cleanmd - 使用 Google Gemini 清洗 OCR 生成的 Markdown 文件

This module provides functionality to clean and format Markdown files
using Google's Gemini API.
"""

__version__ = "0.1.0"

from cleanmd.config import Config, config
from cleanmd.cleaner import MarkdownCleaner
from cleanmd.splitter import MarkdownSplitter
from cleanmd.converter import MarkdownConverter
from cleanmd.utils import count_text_length
from cleanmd.processor import process_markdown

__all__ = [
    "Config",
    "config",
    "MarkdownCleaner",
    "MarkdownSplitter",
    "MarkdownConverter",
    "count_text_length",
    "process_markdown",
]
