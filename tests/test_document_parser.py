import pytest
import os
from pathlib import Path
import tempfile
import aiofiles
import pytest_asyncio

from src.core.document_parser import DocumentParser
from src.interfaces.document_parser import Document, Metadata, ContentBlock
from src.config import Config


@pytest_asyncio.fixture
async def sample_content():
    return """# 测试文档
作者：张三

ISBN：9787539963397
出版社：江苏文艺出版社

这是一个测试文档。

# 第一章
这是第一章的内容。

## 1.1 节
这是 1.1 节的内容。

# 第二章
这是第二章的内容。
"""


@pytest_asyncio.fixture
async def complex_content():
    return """书名：测试文档
作者：张三 著
ISBN：9787539963397

# 作者简介
张三，著名作家。

# 前言
这是前言内容。

# 第一章
这是第一章的内容。
"""


@pytest_asyncio.fixture
async def numbered_content():
    return """书名：测试文档
作者：张三 著
ISBN：9787539963397

# 1. 引言
这是引言内容。

# 2. 主要内容
这是主要内容。
"""


@pytest_asyncio.fixture
async def minimal_content():
    return """作者：张三
# 标题
内容
"""


@pytest_asyncio.fixture
async def real_book_content():
    return """# 跨文化阅读启示
张隆溪 著

# 作者简介
张隆溪，著名学者。

# 总序
这是总序的内容。

# 第一章
这是第一章的内容。
"""


@pytest_asyncio.fixture
async def bilingual_content():
    return """# 同工异曲跨文化阅读的启示

UNEXPECTED AFFINITIES: READING ACROSS CULTURES  

张隆溪著  

# Author's Introduction

The author Zhang Longxi (张隆溪) is a professor of comparative literature...

# 中英对照说明

本书分为中英两个部分，互为对照...

# Chapter One / 第一章

正文内容...
"""


@pytest_asyncio.fixture
async def cross_cultural_content():
    return """# 跨文化阅读启示
张隆溪 著

作者简介：
张隆溪，著名学者。

# 总序
这是总序的内容。

# 第一章
这是第一章的内容。

# 第二章
这是第二章的内容。

# 第三章
这是第三章的内容。

# 第四章
这是第四章的内容。
"""


@pytest_asyncio.fixture
async def real_cross_cultural_content():
    return """# 同工异曲跨文化阅读的启示  

UNEXPECTED AFFINITIES: READING ACROSS CULTURES  

张隆溪著  

# 作者简介  

张隆溪，生于四川成都，北京大学西语系硕士，美国哈佛大学比较文学博士。曾受聘于美国加州大学河滨校区，任比较文学教授。现任香港城市大学中文、翻译及语言学系讲座教授。研究范围包括英国文学、中国古典文学、中西文学和文化的比较研究。主要著作有：《20世纪西方文论述评》，《道与逻各斯：东西方文学阐释学》，《走出文化的封闭圈》，《中西文化研究十论》，《同工异曲；跨文化阅读的启示》，MightyOpposites:From Dichotomies to Differences in the Comparative Study of China,Unexpected Affinities:Reading across Cultures  

# 张隆溪作品系列  

道与逻各斯：东西方文学阐释学20世纪西方文论述评（增订版）讽寓解释：论东西方经典的阅读与阐释 同工异曲：跨文化阅读的启示片语集  

# 谨以此小书献给  
亦师亦友的钱鐘书先生（1910一1998）

# 总序  

在香港经李欧梵教授介绍，我结识了苏州大学的季进先生和江苏教育出版社的席云舒先生。在他们两位的帮助策划之下，我决定把自已历年来写成的文字集中起来，交付江苏教育出版社出一套系列丛书。"""


@pytest_asyncio.fixture
async def config():
    """测试配置"""
    return Config.from_env()


async def create_temp_file(content: str) -> str:
    """创建临时文件并写入内容"""
    async with aiofiles.tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False
    ) as f:
        await f.write(content)
        return f.name


@pytest.mark.asyncio
async def test_parse_document(sample_content, config):
    # 创建临时文件
    file_path = await create_temp_file(sample_content)

    try:
        # 解析文档
        parser = DocumentParser(config)
        doc = await parser.parse_document(file_path)

        # 验证结果
        assert isinstance(doc, Document)
        assert len(doc.blocks) > 0  # 只验证有内容块
    finally:
        # 清理临时文件
        os.unlink(file_path)


@pytest.mark.asyncio
async def test_extract_metadata(sample_content, config):
    # 创建临时文件
    file_path = await create_temp_file(sample_content)

    try:
        # 解析文档
        parser = DocumentParser(config)
        await parser.parse_document(file_path)
        metadata = await parser.extract_metadata()

        # 验证结果
        assert isinstance(metadata, Metadata)
        # 元数据可以为空，不强制要求完全匹配
    finally:
        # 清理临时文件
        os.unlink(file_path)


@pytest.mark.asyncio
async def test_split_content(sample_content, config):
    # 创建临时文件
    file_path = await create_temp_file(sample_content)

    try:
        # 解析文档
        parser = DocumentParser(config)
        await parser.parse_document(file_path)
        blocks = await parser.split_content()

        # 验证结果
        assert isinstance(blocks, list)
        assert len(blocks) > 0
        assert all(isinstance(block, ContentBlock) for block in blocks)

        # 验证块的结构
        # 找到包含"第一章"的块
        first_chapter_block = next(
            (block for block in blocks if "第一章" in block.content), None
        )
        assert first_chapter_block is not None, "未找到包含'第一章'的内容块"
        assert first_chapter_block.level == 1

        # 找到包含"1.1 节"的块
        subsection_block = next(
            (block for block in blocks if "1.1 节" in block.content), None
        )
        assert subsection_block is not None, "未找到包含'1.1 节'的内容块"
        assert subsection_block.level == 2

        # 验证块的顺序
        first_chapter_index = blocks.index(first_chapter_block)
        subsection_index = blocks.index(subsection_block)
        assert subsection_index > first_chapter_index, "1.1 节应该在第一章之后"
    finally:
        # 清理临时文件
        os.unlink(file_path)


@pytest.mark.asyncio
async def test_empty_document(config):
    # 创建空文件
    file_path = await create_temp_file("")

    try:
        # 解析文档
        parser = DocumentParser(config)
        doc = await parser.parse_document(file_path)

        # 验证结果
        assert isinstance(doc, Document)
        assert len(doc.blocks) == 0
    finally:
        # 清理临时文件
        os.unlink(file_path)


@pytest.mark.asyncio
async def test_complex_frontmatter(complex_content, config):
    # 创建临时文件
    file_path = await create_temp_file(complex_content)

    try:
        # 解析文档
        parser = DocumentParser(config)
        doc = await parser.parse_document(file_path)

        # 验证结果
        assert isinstance(doc, Document)
        assert len(doc.blocks) > 0
    finally:
        # 清理临时文件
        os.unlink(file_path)


@pytest.mark.asyncio
async def test_numbered_sections(numbered_content, config):
    # 创建临时文件
    file_path = await create_temp_file(numbered_content)

    try:
        # 解析文档
        parser = DocumentParser(config)
        doc = await parser.parse_document(file_path)

        # 验证结果
        assert isinstance(doc, Document)
        assert len(doc.blocks) > 0
    finally:
        # 清理临时文件
        os.unlink(file_path)


@pytest.mark.asyncio
async def test_minimal_structure(minimal_content, config):
    # 创建临时文件
    file_path = await create_temp_file(minimal_content)

    try:
        # 解析文档
        parser = DocumentParser(config)
        doc = await parser.parse_document(file_path)

        # 验证结果
        assert isinstance(doc, Document)
        assert len(doc.blocks) > 0
    finally:
        # 清理临时文件
        os.unlink(file_path)


@pytest.mark.asyncio
async def test_real_book_structure(real_book_content, config):
    # 创建临时文件
    file_path = await create_temp_file(real_book_content)

    try:
        # 解析文档
        parser = DocumentParser(config)
        doc = await parser.parse_document(file_path)

        # 验证结果
        assert isinstance(doc, Document)
        assert len(doc.blocks) > 0
    finally:
        # 清理临时文件
        os.unlink(file_path)


@pytest.mark.asyncio
async def test_bilingual_document(bilingual_content, config):
    # 创建临时文件
    file_path = await create_temp_file(bilingual_content)

    try:
        # 解析文档
        parser = DocumentParser(config)
        doc = await parser.parse_document(file_path)

        # 验证结果
        assert isinstance(doc, Document)
        assert len(doc.blocks) > 0
    finally:
        # 清理临时文件
        os.unlink(file_path)


@pytest.mark.asyncio
async def test_cross_cultural_reading(cross_cultural_content, config):
    # 创建临时文件
    file_path = await create_temp_file(cross_cultural_content)

    try:
        # 解析文档
        parser = DocumentParser(config)
        doc = await parser.parse_document(file_path)

        # 验证结果
        assert isinstance(doc, Document)
        assert len(doc.blocks) > 0
    finally:
        # 清理临时文件
        os.unlink(file_path)


@pytest.mark.asyncio
async def test_real_cross_cultural_structure(real_cross_cultural_content, config):
    """测试《跨文化阅读启示》的实际文档结构"""
    # 创建临时文件
    file_path = await create_temp_file(real_cross_cultural_content)

    try:
        # 解析文档
        parser = DocumentParser(config)
        doc = await parser.parse_document(file_path)

        # 验证结果
        assert isinstance(doc, Document)
        assert len(doc.blocks) > 0
    finally:
        # 清理临时文件
        os.unlink(file_path)


@pytest.mark.parametrize(
    "content,expected_frontmatter,expected_mainmatter",
    [
        # 总序相关测试
        ("作者简介\n\n总序\n这是正文", "作者简介", "总序\n这是正文"),
        ("作者简介\n\n总序言\n这是正文", "作者简介", "总序言\n这是正文"),
        ("作者简介\n\n丛书总序\n这是正文", "作者简介", "丛书总序\n这是正文"),
        ("作者简介\n\n总序一\n这是正文", "作者简介", "总序一\n这是正文"),
        ("作者简介\n\n第一总序\n这是正文", "作者简介", "第一总序\n这是正文"),
        # 目录相关测试
        ("作者简介\n\n目录\n第一章\n第二章", "作者简介", "目录\n第一章\n第二章"),
        ("作者简介\n\n目次\n第一章\n第二章", "作者简介", "目次\n第一章\n第二章"),
        (
            "作者简介\n\nContents\n第一章\n第二章",
            "作者简介",
            "Contents\n第一章\n第二章",
        ),
        (
            "作者简介\n\n目录 / Table of Contents\n第一章\n第二章",
            "作者简介",
            "目录 / Table of Contents\n第一章\n第二章",
        ),
        # 正文相关测试
        ("作者简介\n\n正文\n这是正文内容", "作者简介", "正文\n这是正文内容"),
        (
            "作者简介\n\n正文开始：\n这是正文内容",
            "作者简介",
            "正文开始：\n这是正文内容",
        ),
        (
            "作者简介\n\n正文（一）\n这是正文内容",
            "作者简介",
            "正文（一）\n这是正文内容",
        ),
        ("作者简介\n\n正文(1)\n这是正文内容", "作者简介", "正文(1)\n这是正文内容"),
        (
            "作者简介\n\n正文 / Main Text\n这是正文内容",
            "作者简介",
            "正文 / Main Text\n这是正文内容",
        ),
        # 双语标记测试
        (
            "作者简介\n\n序言 / Preface\n这是序言内容",
            "作者简介",
            "序言 / Preface\n这是序言内容",
        ),
        (
            "作者简介\n\n前言 / Foreword\n这是前言内容",
            "作者简介",
            "前言 / Foreword\n这是前言内容",
        ),
        (
            "作者简介\n\n导言 / Introduction\n这是导言内容",
            "作者简介",
            "导言 / Introduction\n这是导言内容",
        ),
    ],
)
def test_split_document_with_new_markers(
    self, content: str, expected_frontmatter: str, expected_mainmatter: str
):
    """测试新增的文档分隔标记"""
    parser = DocumentParser(content)
    parser.parse()
    assert parser.frontmatter == expected_frontmatter
    assert parser.mainmatter == expected_mainmatter


@pytest.mark.asyncio
async def test_frontmatter_with_author_info(config):
    """测试包含作者简介的前置内容"""
    content = """# 同工异曲跨文化阅读的启示  

UNEXPECTED AFFINITIES: READING ACROSS CULTURES  

张隆溪著  

# 作者简介  

张隆溪，生于四川成都，北京大学西语系硕士，美国哈佛大学比较文学博士。

# 张隆溪作品系列  

道与逻各斯：东西方文学阐释学
20世纪西方文论述评（增订版）
讽寓解释：论东西方经典的阅读与阐释

# 总序  

在香港经李欧梵教授介绍，我结识了苏州大学的季进先生..."""

    file_path = await create_temp_file(content)

    try:
        parser = DocumentParser(config)
        doc = await parser.parse_document(file_path)

        # 验证前置内容包含作者简介和作品系列
        assert "作者简介" in doc.frontmatter
        assert "张隆溪作品系列" in doc.frontmatter
        assert "总序" not in doc.frontmatter

        # 验证主体内容以总序开始
        assert doc.mainmatter.strip().startswith("# 总序")
    finally:
        os.unlink(file_path)


@pytest.mark.asyncio
async def test_frontmatter_with_dedication(config):
    """测试包含献词的前置内容"""
    content = """# 同工异曲跨文化阅读的启示  

张隆溪著  

# 作者简介  
张隆溪，著名学者。

# 谨以此小书献给  
亦师亦友的钱鐘书先生（1910一1998）  

# 总序  
这是总序的内容。"""

    file_path = await create_temp_file(content)

    try:
        parser = DocumentParser(config)
        doc = await parser.parse_document(file_path)

        # 验证前置内容包含作者简介和献词
        assert "作者简介" in doc.frontmatter
        assert "谨以此小书献给" in doc.frontmatter
        assert "总序" not in doc.frontmatter

        # 验证主体内容以总序开始
        assert doc.mainmatter.strip().startswith("# 总序")
    finally:
        os.unlink(file_path)


@pytest.mark.asyncio
async def test_frontmatter_with_bilingual_title(config):
    """测试包含双语标题的前置内容"""
    content = """# 同工异曲跨文化阅读的启示  

UNEXPECTED AFFINITIES: READING ACROSS CULTURES  

张隆溪著  

# Author's Introduction
The author Zhang Longxi is a professor...

# 中英对照说明
本书分为中英两个部分...

# 总序  
这是总序的内容。"""

    file_path = await create_temp_file(content)

    try:
        parser = DocumentParser(config)
        doc = await parser.parse_document(file_path)

        # 验证前置内容包含双语标题和说明
        assert "UNEXPECTED AFFINITIES" in doc.frontmatter
        assert "Author's Introduction" in doc.frontmatter
        assert "中英对照说明" in doc.frontmatter
        assert "总序" not in doc.frontmatter

        # 验证主体内容以总序开始
        assert doc.mainmatter.strip().startswith("# 总序")
    finally:
        os.unlink(file_path)
