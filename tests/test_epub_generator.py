import pytest
import os
from pathlib import Path
import tempfile
import pytest_asyncio
import zipfile
import yaml
from PIL import Image
import aiohttp
import asyncio
from unittest.mock import Mock, patch

from src.core.epub_generator import EPUBGenerator
from src.interfaces.document_parser import Document, Metadata, ContentBlock
from src.config import Config


@pytest_asyncio.fixture
async def config():
    """测试配置"""
    return Config.from_env()


@pytest_asyncio.fixture
async def sample_document():
    """示例文档"""
    metadata = Metadata(
        title="测试文档",
        author="测试作者",
        isbn="9787000000000",
        publisher="测试出版社",
        description="这是一个测试文档。",
    )

    blocks = [
        ContentBlock(
            content="# 第一章\n\n这是第一章的内容。\n\n## 1.1 节\n\n这是 1.1 节的内容。",
            block_type="content",
            level=1,
            position=0,
        ),
        ContentBlock(
            content="# 第二章\n\n这是第二章的内容。\n\n## 2.1 节\n\n这是 2.1 节的内容。",
            block_type="content",
            level=1,
            position=1,
        ),
    ]

    return Document(metadata=metadata, blocks=blocks, raw_content="")


@pytest.mark.asyncio
async def test_epub_generation(config, sample_document):
    """测试 EPUB 生成"""
    generator = EPUBGenerator(config)
    epub_data = await generator.generate(sample_document, sample_document.metadata)

    # 保存到临时文件
    with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as f:
        f.write(epub_data)
        temp_path = f.name

    try:
        # 验证 EPUB 文件结构
        with zipfile.ZipFile(temp_path, "r") as epub:
            # 检查必要文件
            assert "mimetype" in epub.namelist()
            assert "META-INF/container.xml" in epub.namelist()
            assert any(name.endswith("content.opf") for name in epub.namelist())
            assert any(name.endswith("toc.ncx") for name in epub.namelist())
            assert any(name.endswith("nav.xhtml") for name in epub.namelist())

            # 检查内容文件
            content_files = [
                name for name in epub.namelist() if name.endswith(".xhtml")
            ]
            assert len(content_files) >= 2  # 至少应该有两个章节

            # 检查样式文件
            assert any(name.endswith(".css") for name in epub.namelist())

            # 检查元数据
            opf_file = next(
                name for name in epub.namelist() if name.endswith("content.opf")
            )
            opf_content = epub.read(opf_file).decode("utf-8")
            assert "测试文档" in opf_content
            assert "测试作者" in opf_content
            assert "9787000000000" in opf_content
            assert "测试出版社" in opf_content

    finally:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@pytest.mark.asyncio
async def test_epub_validation(config, sample_document):
    """测试 EPUB 验证"""
    generator = EPUBGenerator(config)
    epub_data = await generator.generate(sample_document, sample_document.metadata)

    # 验证输出
    assert await generator.validate_output(epub_data)


@pytest.mark.asyncio
async def test_empty_document(config):
    """测试空文档"""
    metadata = Metadata()
    document = Document(metadata=metadata, blocks=[], raw_content="")

    generator = EPUBGenerator(config)
    epub_data = await generator.generate(document, metadata)

    # 验证基本结构
    with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as f:
        f.write(epub_data)
        temp_path = f.name

    try:
        with zipfile.ZipFile(temp_path, "r") as epub:
            # 检查基本文件结构
            assert "mimetype" in epub.namelist()
            assert "META-INF/container.xml" in epub.namelist()
            assert any(name.endswith("content.opf") for name in epub.namelist())
            assert any(name.endswith("toc.ncx") for name in epub.namelist())
            assert any(name.endswith("nav.xhtml") for name in epub.namelist())
            assert any(name.endswith(".css") for name in epub.namelist())

    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@pytest.mark.asyncio
async def test_metadata_generation(config):
    """测试元数据生成"""
    generator = EPUBGenerator(config)
    metadata = Metadata(
        title="测试文档",
        author="测试作者",
        isbn="9787000000000",
        publisher="测试出版社",
        description="这是一个测试文档。",
    )

    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        metadata_file = temp_dir / "metadata.yaml"

        # 生成元数据文件
        generator._write_metadata(metadata_file, metadata)

        # 读取并验证元数据
        with open(metadata_file) as f:
            data = yaml.safe_load(f)

        # 验证基本元数据
        assert data["title"] == "测试文档"
        assert data["author"] == "测试作者"
        assert isinstance(data["identifier"], list)
        assert data["identifier"][0]["type"] == "isbn"
        assert data["identifier"][0]["text"] == "9787000000000"
        assert data["publisher"] == "测试出版社"
        assert data["description"] == "这是一个测试文档。"
        assert data["language"] == "zh-CN"

        # 验证 EPUB 设置
        assert data["toc"] is True
        assert data["toc-depth"] == 3
        assert data["number-sections"] is True
        assert data["documentclass"] == "book"
        assert isinstance(data["geometry"], dict)
        assert "paperwidth" in data["geometry"]


@pytest_asyncio.fixture
async def document_with_frontmatter():
    """带有前置内容的文档"""
    metadata = Metadata(
        title="跨文化阅读启示",
        author="张隆溪",
        isbn="9787539963397",
        publisher="江苏文艺出版社",
        description="本书探讨了跨文化阅读的重要性和方法。",
    )

    blocks = [
        ContentBlock(
            content="""作者简介：
张隆溪，生于四川成都，北京大学西语系硕士，美国哈佛大学比较文学博士。
现任香港城市大学中文、翻译及语言学系讲座教授。

版权信息：
版权所有 © 2023 张隆溪
江苏文艺出版社出版""",
            block_type="frontmatter",
            level=0,
            position=0,
        ),
        ContentBlock(
            content="# 第一章 跨文化阅读的意义\n\n跨文化阅读是理解不同文化的重要途径。",
            block_type="content",
            level=1,
            position=1,
        ),
        ContentBlock(
            content="# 第二章 跨文化阅读的方法\n\n要进行有效的跨文化阅读，需要注意以下几点。",
            block_type="content",
            level=1,
            position=2,
        ),
    ]

    return Document(metadata=metadata, blocks=blocks, raw_content="")


@pytest.mark.asyncio
async def test_frontmatter_processing(config, document_with_frontmatter):
    """测试前置内容处理"""
    generator = EPUBGenerator(config)

    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        content_file = temp_dir / "content.md"

        # 生成内容文件
        generator._write_content(content_file, document_with_frontmatter)

        # 读取并验证内容
        content = content_file.read_text()

        # 验证前置内容格式
        assert "---" in content  # 检查分隔符
        assert "# 前言" in content  # 检查前言标题
        assert "作者简介" in content  # 检查作者简介
        assert "版权信息" in content  # 检查版权信息

        # 验证章节内容
        assert "# 第一章 跨文化阅读的意义" in content
        assert "# 第二章 跨文化阅读的方法" in content

        # 验证分页标记
        assert "\\newpage" in content


@pytest.mark.asyncio
async def test_metadata_with_cover(config):
    """测试带封面的元数据生成"""
    generator = EPUBGenerator(config)
    metadata = Metadata(
        title="跨文化阅读启示",
        author="张隆溪",
        isbn="9787539963397",
        publisher="江苏文艺出版社",
        description="本书探讨了跨文化阅读的重要性和方法。",
    )
    # 模拟添加封面图片
    setattr(metadata, "cover_image", "cover.jpg")

    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        metadata_file = temp_dir / "metadata.yaml"

        # 生成元数据文件
        generator._write_metadata(metadata_file, metadata)

        # 读取并验证元数据
        with open(metadata_file) as f:
            data = yaml.safe_load(f)

        # 验证基本元数据
        assert data["title"] == "跨文化阅读启示"
        assert data["author"] == "张隆溪"
        assert isinstance(data["identifier"], list)
        assert data["identifier"][0]["type"] == "isbn"
        assert data["identifier"][0]["text"] == "9787539963397"

        # 验证 EPUB 特定设置
        assert data["epub-chapter-level"] == 1
        assert data["epub-cover-image"] == "cover.jpg"
        assert data["papersize"] == "a5"
        assert isinstance(data["geometry"], dict)
        assert data["geometry"]["paperwidth"] == "148mm"

        # 验证字体设置
        assert "Noto Serif CJK SC" in data["CJKmainfont"]
        assert "Noto Sans CJK SC" in data["CJKsansfont"]


@pytest.fixture
def metadata_with_douban():
    """带有豆瓣元数据的夹具"""
    return Metadata(
        title="测试书籍",
        author="测试作者",
        publisher="测试出版社",
        isbn="9787000000000",
        description="这是一本测试书籍",
        douban_metadata={
            "cover_url": "https://img1.doubanio.com/view/subject/l/public/test.jpg",
            "rating": {"average": 8.8, "numRaters": 1000},
            "pubdate": "2024-01",
        },
    )


@pytest.fixture
def temp_cover_image():
    """临时封面图片夹具"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        image_path = temp_dir / "test_cover.jpg"

        # 创建测试图片
        img = Image.new("RGB", (1400, 2100), "white")
        img.save(image_path, "JPEG")

        yield image_path


async def test_process_cover_from_douban(
    epub_generator, metadata_with_douban, monkeypatch
):
    """测试从豆瓣元数据处理封面图片"""

    # 模拟下载图片
    async def mock_download_image(url: str, target_path: Path):
        img = Image.new("RGB", (1400, 2100), "white")
        img.save(target_path)
        return True

    monkeypatch.setattr(epub_generator, "_download_cover_image", mock_download_image)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        cover_path = await epub_generator._process_cover(metadata_with_douban, temp_dir)

        assert cover_path is not None
        assert cover_path.exists()
        assert cover_path.suffix == ".jpg"

        # 验证图片尺寸
        with Image.open(cover_path) as img:
            width, height = img.size
            assert width <= epub_generator.config.cover_width
            assert height <= epub_generator.config.cover_height


async def test_process_cover_with_local_image(
    epub_generator, metadata_with_douban, temp_cover_image
):
    """测试处理本地封面图片"""
    # 设置本地封面图片路径
    metadata_with_douban.cover_image = str(temp_cover_image)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        cover_path = await epub_generator._process_cover(metadata_with_douban, temp_dir)

        assert cover_path is not None
        assert cover_path.exists()
        assert cover_path.suffix == ".jpg"


async def test_process_cover_fallback_to_default(
    epub_generator, metadata_with_douban, monkeypatch
):
    """测试当豆瓣封面下载失败时使用默认封面"""

    # 模拟下载失败
    async def mock_download_image(url: str, target_path: Path):
        return False

    monkeypatch.setattr(epub_generator, "_download_cover_image", mock_download_image)

    # 创建默认封面
    default_cover = epub_generator.config.default_cover
    default_cover.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1400, 2100), "white")
    img.save(default_cover)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        cover_path = await epub_generator._process_cover(metadata_with_douban, temp_dir)

        assert cover_path is not None
        assert cover_path.exists()
        assert cover_path.suffix == ".jpg"


async def test_generate_text_cover(epub_generator, metadata_with_douban):
    """测试生成文字封面"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        images_dir = Path(temp_dir) / "images"
        images_dir.mkdir()

        cover_path = await epub_generator._generate_text_cover(
            metadata_with_douban, images_dir
        )

        assert cover_path is not None
        assert cover_path.exists()
        assert cover_path.suffix == ".jpg"


async def test_epub_generation_with_cover(
    epub_generator, document_with_frontmatter, metadata_with_douban
):
    """测试带封面的 EPUB 生成"""

    # 模拟下载图片
    async def mock_download_image(url: str, target_path: Path):
        img = Image.new("RGB", (1400, 2100), "white")
        img.save(target_path)
        return True

    with patch.object(epub_generator, "_download_cover_image", mock_download_image):
        epub_data = await epub_generator.generate(
            document_with_frontmatter, metadata_with_douban
        )

        assert epub_data is not None
        assert len(epub_data) > 0

        # 验证生成的 EPUB
        assert await epub_generator.validate_output(epub_data)
