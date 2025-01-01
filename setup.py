"""
cleanmd2epub 包安装配置
"""

from setuptools import setup, find_packages

setup(
    name="cleanmd2epub",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.10",
    install_requires=[
        "aiohttp>=3.9.1",
        "pytest>=7.4.3",
        "pytest-asyncio>=0.23.2",
        "python-dotenv>=1.0.0",
        "tenacity>=8.2.3",
        "click>=8.1.0",
        "rich>=13.0.0",
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "ebooklib>=0.18.0",
        "beautifulsoup4>=4.12.0",
        "pandoc>=2.3",
    ],
    extras_require={
        "dev": [
            "black",
            "isort",
            "flake8",
            "mypy",
            "pre-commit",
            "pytest",
            "pytest-asyncio",
            "pytest-cov",
        ],
    },
    entry_points={
        "console_scripts": [
            "cleanmd2epub=src.cli.main:main",
        ],
    },
)
